package datacellar.connector;

import org.eclipse.edc.spi.monitor.Monitor;

import jakarta.ws.rs.Consumes;
import jakarta.ws.rs.GET;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.core.MediaType;

@Consumes({ MediaType.APPLICATION_JSON })
@Produces({ MediaType.APPLICATION_JSON })
@Path("/")
public class DataCellarController {
    private final Monitor monitor;

    public DataCellarController(Monitor monitor) {
        this.monitor = monitor;
    }

    @GET
    @Path("health")
    public String checkHealth() {
        monitor.info("Received a health request");
        return "{\"response\":\"I'm alive!\"}";
    }
}
