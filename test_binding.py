#!/usr/bin/env python3
"""Test script to verify RabbitMQ queue binding is working correctly."""

import asyncio
import logging
from edcpy.messaging import ConsumerQueueFactory, with_consumer_messaging_app
from edcpy.message_handler import create_message_handler, create_handler_function
from edcpy.messaging import HttpPullMessage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_message_receipt():
    """Test that we can receive a message on the bound queue."""
    
    # Create consumer-specific queue configuration
    queue_factory = ConsumerQueueFactory()
    queue_config = queue_factory.create_pull_queue_config(
        consumer_id="test-consumer",
        auto_delete=True,
    )
    
    logger.info(f"Created test queue '{queue_config.queue_name}' with routing key '{queue_config.routing_key}'")
    
    # Create message handler
    message_handler = create_message_handler(
        message_class=HttpPullMessage,
        auto_acknowledge=False,
    )
    
    # Create handler function
    handler_func = create_handler_function(message_handler)
    
    # Start messaging app and wait for messages
    async with with_consumer_messaging_app(
        queue_config=queue_config,
        handler=handler_func,
    ):
        logger.info("Test consumer started, waiting for messages...")
        
        try:
            # Wait for any message with a short timeout
            async with message_handler.process_message(timeout_seconds=5) as msg:
                logger.info(f"Received message: {msg.id}")
                return msg
        except asyncio.TimeoutError:
            logger.warning("No message received within timeout")
            return None

if __name__ == "__main__":
    result = asyncio.run(test_message_receipt())
    if result:
        print(f"✓ Successfully received message: {result.id}")
    else:
        print("✗ No message received")