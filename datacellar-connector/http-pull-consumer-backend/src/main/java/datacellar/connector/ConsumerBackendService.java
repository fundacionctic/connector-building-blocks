package datacellar.connector;

import java.io.IOException;
import java.net.InetSocketAddress;
import java.util.Optional;

import com.sun.net.httpserver.HttpServer;

/**
 * This class is responsible for starting the Consumer Backend Service
 * and registering the ConsumerBackendReceiverHandler to handle HTTP requests.
 */
public class ConsumerBackendService {

    /**
     * This is the port on which the Consumer Backend Service will listen for HTTP
     * requests. It is read from the environment variable "server.port". If the
     * environment variable is not set, the default value of 4000 is used.
     */
    static final String HTTP_PORT = "server.port";

    /**
     * This method starts the Consumer Backend Service and registers the
     * ConsumerBackendReceiverHandler to handle HTTP requests.
     * 
     * @param args The command line arguments passed to the application.
     */
    public static void main(String[] args) {
        int port = Integer.parseInt(Optional.ofNullable(System.getenv(HTTP_PORT)).orElse("4000"));
        var server = createHttpServer(port);
        server.createContext("/receiver", new ConsumerBackendReceiverHandler());
        server.setExecutor(null);
        server.start();
        System.out.println("server started at " + port);
    }

    private static HttpServer createHttpServer(int port) {
        try {
            return HttpServer.create(new InetSocketAddress(port), 0);
        } catch (IOException e) {
            throw new RuntimeException("Unable to start server at port " + port, e);
        }
    }
}