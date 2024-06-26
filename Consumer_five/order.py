import json
import logging
import pymongo
import pika
import random

# Connect to MongoDB
client = pymongo.MongoClient('enter your mongo db connection string here')
db = client["database"]
collection = db["inventory"]
orders = db["orders"]

# RabbitMQ setup
credentials = pika.PlainCredentials(username='guest', password='guest')
parameters = pika.ConnectionParameters(host='rabbitmq', port=5672, credentials=credentials)
connection = pika.BlockingConnection(parameters=parameters)
channel = connection.channel()

# Declare the "create_order" queue
channel.queue_declare(queue='create_order', durable=True)

# Define a callback function to handle incoming messages
def callback(ch, method, properties, body):
    # Parse incoming message
    body = body.decode()
    body = json.loads(body)

    order_id = random.randint(100000, 999999)
    try:
        record = {
            "order_id": order_id,
            "product_id": body['product_id'],
            "units": body['units'],
        }
        orders.insert_one(record)
        print("Order created: ", record)
    except Exception as e:
        print("Error creating order: ", e)

    try:
        # Update the inventory
        product_id = body['product_id']
        units = body['units']
        inventory = collection.find_one({"product_id": product_id})
        if inventory is None:
            print("No inventory record found for product_id: ", product_id)
        else:
            new_units = int(inventory['units']) - int(units)
            if new_units < 0:
                print("Not enough units in inventory for product_id: ", product_id)
            else:
                collection.update_one(
                    {"product_id": product_id},
                    {"$set": {"units": new_units}}
                )
                print("Inventory updated: ", {"product_id": product_id, "units": new_units})
    except Exception as e:
        print("Error updating inventory: ", e)
        
    # Acknowledge the message
    ch.basic_ack(delivery_tag=method.delivery_tag)

# Start consuming messages from the "create_order" queue
channel.basic_consume(queue='create_order', on_message_callback=callback)

print('Waiting for messages...')
channel.start_consuming()