import asyncio
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Callable, Generic, TypeVar, Union

from faststream.rabbit import RabbitMessage
from pydantic import BaseModel

_logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


@dataclass
class BrokerMessage(Generic[T]):
    """Context for a message received from the Rabbit broker."""

    message: T
    rabbit_message: RabbitMessage


class MessageHandler(Generic[T]):
    """
    A utility class for handling RabbitMQ messages with consistent ack/nack behavior.
    """

    def __init__(
        self,
        message_class: type[T],
        auto_acknowledge: bool = False,
        max_nack_attempts: int = 5,
    ):
        """
        Initialize the MessageHandler.

        Args:
            message_class: The Pydantic model class for the message type
            auto_acknowledge: Whether auto-acknowledgment is enabled in the messaging system.
                            If True, manual ack/nack calls will be skipped to avoid errors.
            max_nack_attempts: Maximum number of times to nack a message before giving up.
                             After this limit, messages will be acked to prevent infinite loops.
        """

        self.message_class = message_class
        self.auto_acknowledge = auto_acknowledge
        self.max_nack_attempts = max_nack_attempts
        self.queue: asyncio.Queue[BrokerMessage[T]] = asyncio.Queue()
        # Track nack attempts per message ID to prevent infinite loops
        self.nack_attempts: dict[str, int] = {}

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
                message.dict() if hasattr(message, "dict") else str(message),
            )

            broker_message = BrokerMessage(
                message=message, rabbit_message=rabbit_message
            )

            await self.queue.put(broker_message)
        except Exception as e:
            _logger.error("Failed to parse message: %s", e)
            await self._safe_nack(rabbit_message)

    async def wait_for_message(
        self, timeout_seconds: int, expected_id: Union[str, None] = None
    ) -> BrokerMessage[T]:
        """
        Wait for a message from the queue, optionally filtering by ID.

        Messages that don't match the expected ID are immediately nacked
        to make them available to other consumers ASAP.

        Args:
            timeout_seconds: Timeout for waiting for messages
            expected_id: If provided, only return messages with this ID

        Returns:
            BrokerMessage containing the matched message

        Raises:
            asyncio.TimeoutError: If no matching message is received within timeout
        """

        if expected_id is None:
            # Simple case: return the first message
            broker_message = await asyncio.wait_for(
                self.queue.get(), timeout=timeout_seconds
            )

            return broker_message

        # Complex case: wait for a message with the expected ID
        while True:
            broker_message = await asyncio.wait_for(
                self.queue.get(), timeout=timeout_seconds
            )

            message_id = self._extract_message_id(broker_message.message)

            if message_id == expected_id:
                return broker_message

            # Check nack attempts to prevent infinite loops
            current_attempts = self.nack_attempts.get(message_id, 0)

            if current_attempts >= self.max_nack_attempts:
                _logger.warning(
                    "Message ID (%s) has been nacked %d times, acking to prevent infinite loop",
                    message_id,
                    current_attempts,
                )

                # Ack the message to remove it from the queue permanently
                await self._safe_ack(broker_message.rabbit_message)
                continue

            _logger.warning(
                "Message ID (%s) does not match expected ID (%s), nacking immediately (attempt %d/%d)",
                message_id,
                expected_id,
                current_attempts + 1,
                self.max_nack_attempts,
            )

            # Increment nack attempts counter
            self.nack_attempts[message_id] = current_attempts + 1

            # Nack immediately to make it available to other consumers
            await self._safe_nack(broker_message.rabbit_message)

    def _extract_message_id(self, message: T) -> str:
        """
        Extract the ID from a message. Override this method for custom ID extraction.

        Args:
            message: The parsed message object

        Returns:
            The message ID as a string
        """

        if hasattr(message, "id"):
            return getattr(message, "id")
        elif hasattr(message, "transfer_process_id"):
            return getattr(message, "transfer_process_id")
        else:
            raise AttributeError(
                f"Message {type(message)} has no recognizable ID field"
            )

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

    def clear_nack_attempts(self) -> None:
        """
        Clear the nack attempts counter.

        This can be called periodically to prevent the dict from growing indefinitely.
        Only call this when you're sure no messages are being redelivered.
        """

        _logger.debug(
            "Clearing nack attempts counter (had %d entries)", len(self.nack_attempts)
        )

        self.nack_attempts.clear()

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

        Example:
            async with handler.process_message(timeout=30, expected_id="transfer-123") as message:
                # Process the message
                await make_http_request(message.request_args)
                # Message is automatically acked on successful completion
        """

        broker_message = await self.wait_for_message(timeout_seconds, expected_id)

        try:
            yield broker_message.message

            # If we get here, processing was successful
            await self._safe_ack(broker_message.rabbit_message)

            # Remove from nack attempts since we successfully processed it
            if expected_id is not None:
                self.nack_attempts.pop(expected_id, None)

        except Exception as e:
            _logger.error("Error processing message: %s", e)
            await self._safe_nack(broker_message.rabbit_message)

            # Increment nack attempts to track failed processing
            if expected_id is not None:
                current_attempts = self.nack_attempts.get(expected_id, 0)
                self.nack_attempts[expected_id] = current_attempts + 1

            raise


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
