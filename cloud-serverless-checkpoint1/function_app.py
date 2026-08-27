import azure.functions as func
import logging
import json

app = func.FunctionApp()


@app.service_bus_topic_trigger(
    arg_name="message",
    topic_name="orders",
    subscription_name="orders-subscription",
    connection="SERVICE_BUS_CONNECTION"
)
def process_order(message: func.ServiceBusMessage):

    body = message.get_body().decode("utf-8")

    order = json.loads(body)

    logging.info("================================")
    logging.info("Pedido recebido do Service Bus")
    logging.info("================================")

    logging.info(f"Order ID: {order.get('order_id')}")
    logging.info(f"Cliente: {order.get('customer')}")
    logging.info(f"Produto: {order.get('product')}")
    logging.info(f"Quantidade: {order.get('quantity')}")

    logging.info("Pedido processado com sucesso.")