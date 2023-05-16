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
    private final String logPrefix;

    public DataCellarController(Monitor monitor, String logPrefix) {
        this.monitor = monitor;
        this.logPrefix = logPrefix;
    }

    @GET
    @Path("health")
    public String checkHealth() {
        monitor.info(String.format("%s :: Received a health request", logPrefix));
        return "{\"response\":\"I'm alive!\"}";
    }
}
