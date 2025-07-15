import asyncio
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import (
    Any,
    AsyncGenerator,
    Callable,
    Generic,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
)

from faststream.rabbit import RabbitMessage
from pydantic import BaseModel

_logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


@dataclass
class BrokerMessage(Generic[T]):
    """Context for a message received from the Rabbit broker."""

    message: T
    rabbit_message: RabbitMessage
    consumed: bool = False


class MessageHandler(Generic[T]):
    """A unified message handler for RabbitMQ messages with optional filtering."""

    def __init__(
        self,
        message_class: Type[T],
        auto_acknowledge: bool = False,
    ):
        """
        Initialize the MessageHandler.

        Args:
            message_class: The Pydantic model class for the message type
            auto_acknowledge: Whether auto-acknowledgment is enabled in the messaging system
        """

        self.auto_acknowledge = auto_acknowledge
        self.message_class = message_class
        self.messages: List[BrokerMessage[T]] = []
        self._lock = asyncio.Lock()

    async def _safe_ack(self, rabbit_message: RabbitMessage) -> None:
        """Safely acknowledge a message, handling auto-acknowledge mode."""

        if not self.auto_acknowledge:
            try:
                await rabbit_message.ack()
            except Exception as e:
                _logger.warning("Failed to ack message: %s", e)
        else:
            _logger.debug("Auto-acknowledge enabled, skipping manual ack")

    async def _safe_nack(self, rabbit_message: RabbitMessage) -> None:
        """Safely nack a message, handling auto-acknowledge mode."""

        if not self.auto_acknowledge:
            try:
                await rabbit_message.nack()
            except Exception as e:
                _logger.warning("Failed to nack message: %s", e)
        else:
            _logger.debug("Auto-acknowledge enabled, skipping manual nack")

    async def handle_message(
        self, payload: dict, rabbit_message: RabbitMessage
    ) -> None:
        """
        Handle an incoming message by parsing it and putting it into the queue.

        Args:
            payload: The message payload dictionary
            rabbit_message: The RabbitMessage for ack/nack operations
        """

        try:
            message = self.message_class(**payload)

            _logger.info(
                "Received %s message:\n%s",
                self.message_class.__name__,
                (
                    message.model_dump()
                    if hasattr(message, "model_dump")
                    else str(message)
                ),
            )

            broker_message = BrokerMessage(
                message=message, rabbit_message=rabbit_message
            )

            async with self._lock:
                self.messages.append(broker_message)

            message_id = self._extract_message_id(message)

            _logger.debug(
                "Added message with ID '%s' to handler storage",
                message_id or "None",
            )
        except Exception as e:
            _logger.error("Failed to parse message: %s", e)
            await self._safe_nack(rabbit_message)

    async def wait_for_message(
        self, timeout_seconds: int, expected_id: Union[str, None] = None
    ) -> BrokerMessage[T]:
        """
        Wait for a message from the storage, optionally filtering by ID.
        Messages remain in storage until explicitly consumed via mark_consumed().

        Args:
            timeout_seconds: Timeout for waiting for messages
            expected_id: If provided, only return messages with this ID

        Returns:
            BrokerMessage containing the matched message

        Raises:
            asyncio.TimeoutError: If no matching message is received within timeout
        """

        start_time = asyncio.get_event_loop().time()

        while True:
            current_time = asyncio.get_event_loop().time()

            if current_time - start_time >= timeout_seconds:
                raise asyncio.TimeoutError("Timeout waiting for message")

            async with self._lock:
                # Look for unconsumed messages
                for broker_message in self.messages:
                    if broker_message.consumed:
                        continue

                    # If no specific ID is expected, return any unconsumed message
                    if expected_id is None:
                        return broker_message

                    # If specific ID is expected, check for match
                    message_id = self._extract_message_id(broker_message.message)

                    # If message has no ID but expected_id is provided, skip this message
                    if message_id is None:
                        continue

                    if message_id == expected_id:
                        return broker_message

            # No matching message found, wait a bit before checking again
            await asyncio.sleep(0.1)

    async def mark_consumed(self, broker_message: BrokerMessage[T]) -> None:
        """
        Mark a message as consumed and remove it from storage.

        Args:
            broker_message: The message to mark as consumed
        """
        async with self._lock:
            broker_message.consumed = True
            # Clean up consumed messages periodically
            self.messages = [msg for msg in self.messages if not msg.consumed]

    def _extract_message_id(self, message: T) -> Optional[str]:
        """
        Extract the ID from a message. Returns None if message has no ID field.

        Args:
            message: The parsed message object

        Returns:
            The message ID as a string, or None if no ID field exists
        """

        if hasattr(message, "id"):
            return getattr(message, "id")
        elif hasattr(message, "transfer_process_id"):
            return getattr(message, "transfer_process_id")
        else:
            return None

    @asynccontextmanager
    async def process_message(
        self, timeout_seconds: int, expected_id: Union[str, None] = None
    ) -> AsyncGenerator[T, None]:
        """
        Context manager for processing a message with automatic ack/nack handling.

        Args:
            timeout_seconds: Timeout for waiting for messages
            expected_id: If provided, only process messages with this ID

        Yields:
            The parsed message object
        """

        broker_message = await self.wait_for_message(timeout_seconds, expected_id)

        try:
            yield broker_message.message
            await self._safe_ack(broker_message.rabbit_message)
            await self.mark_consumed(broker_message)
        except Exception as e:
            _logger.error("Error processing message: %s", e)
            await self._safe_nack(broker_message.rabbit_message)
            await self.mark_consumed(broker_message)
            raise


def create_message_handler(
    message_class: Type[T],
    auto_acknowledge: bool = False,
) -> MessageHandler[T]:
    """Create a message handler (filtering is controlled by passing expected_id to wait_for_message)."""

    return MessageHandler(
        message_class=message_class,
        auto_acknowledge=auto_acknowledge,
    )


def create_handler_function(
    message_handler: MessageHandler[T],
) -> Callable[[dict, RabbitMessage], Any]:
    """
    Create a handler function that can be used with the messaging system.

    Args:
        message_handler: The MessageHandler instance to use

    Returns:
        An async function that can be passed to the messaging system
    """

    async def handler(payload: dict, msg: RabbitMessage) -> None:
        await message_handler.handle_message(payload, msg)

    return handler


class MessageConsumer:
    """Simplified consumer interface for message operations."""

    def __init__(self, handler: MessageHandler, default_timeout: int = 60):
        """Initialize the message consumer.

        Args:
            handler: The MessageHandler instance to use
            default_timeout: Default timeout for message operations
        """

        self.handler = handler
        self.default_timeout = default_timeout

    async def get_message(
        self, expected_id: Optional[str] = None, timeout: Optional[int] = None
    ):
        """Get a message with automatic ack/nack handling.

        Args:
            expected_id: If provided, only return messages with this ID.
                        Note: Some message types (like HttpPushMessage) don't have IDs.
            timeout: Timeout for waiting for messages (uses default if None)

        Returns:
            The parsed message object
        """

        timeout = timeout or self.default_timeout

        async with self.handler.process_message(timeout, expected_id) as msg:
            return msg

    @asynccontextmanager
    async def wait_for_message(
        self, expected_id: Optional[str] = None, timeout: Optional[int] = None
    ):
        """Context manager for message processing with automatic ack/nack.

        Args:
            expected_id: If provided, only process messages with this ID.
                        Note: Some message types (like HttpPushMessage) don't have IDs.
            timeout: Timeout for waiting for messages (uses default if None)

        Yields:
            The parsed message object
        """

        timeout = timeout or self.default_timeout

        async with self.handler.process_message(timeout, expected_id) as msg:
            yield msg
