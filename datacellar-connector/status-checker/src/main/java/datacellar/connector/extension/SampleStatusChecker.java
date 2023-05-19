package datacellar.connector.extension;

import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.List;
import java.util.Optional;

import org.eclipse.edc.connector.transfer.spi.types.ProvisionedResource;
import org.eclipse.edc.connector.transfer.spi.types.StatusChecker;
import org.eclipse.edc.connector.transfer.spi.types.TransferProcess;
import org.eclipse.edc.spi.types.domain.DataAddress;

public class SampleStatusChecker implements StatusChecker {
    @Override
    public boolean isComplete(TransferProcess transferProcess, List<ProvisionedResource> resources) {
        DataAddress destination = transferProcess.getDataRequest().getDataDestination();
        var path = destination.getProperty("path");

        return Optional.ofNullable(path)
                .map(this::checkPath)
                .orElse(false);
    }

    private boolean checkPath(String path) {
        return Files.exists(Paths.get(path));
    }
}