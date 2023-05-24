
package datacellar.connector;

import java.io.IOException;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpHandler;

/**
 * This class is responsible for handling the HTTP request received by the
 * Consumer Backend Service.
 */
public class ConsumerBackendReceiverHandler implements HttpHandler {

    /**
     * This method just prints the request body to the console and returns a 200 OK
     * response.
     */
    @Override
    public void handle(HttpExchange exchange) throws IOException {
        System.out.println("Request Body: " + new String(exchange.getRequestBody().readAllBytes()));
        exchange.sendResponseHeaders(200, 0);
    }
}