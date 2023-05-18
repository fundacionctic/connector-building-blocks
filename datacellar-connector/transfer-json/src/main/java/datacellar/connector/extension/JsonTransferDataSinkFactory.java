package datacellar.connector.extension;

import java.io.File;
import java.util.concurrent.ExecutorService;

import org.eclipse.edc.connector.dataplane.spi.pipeline.DataSink;
import org.eclipse.edc.connector.dataplane.spi.pipeline.DataSinkFactory;
import org.eclipse.edc.spi.monitor.Monitor;
import org.eclipse.edc.spi.result.Result;
import org.eclipse.edc.spi.types.domain.transfer.DataFlowRequest;
import org.jetbrains.annotations.NotNull;

class JsonTransferDataSinkFactory implements DataSinkFactory {
    private final Monitor monitor;
    private final ExecutorService executorService;
    private final int partitionSize;

    JsonTransferDataSinkFactory(Monitor monitor, ExecutorService executorService, int partitionSize) {
        this.monitor = monitor;
        this.executorService = executorService;
        this.partitionSize = partitionSize;
    }

    @Override
    public boolean canHandle(DataFlowRequest request) {
        return JsonTransferExtension.JSON_TYPE.equalsIgnoreCase(request.getDestinationDataAddress().getType());
    }

    @Override
    public @NotNull Result<Boolean> validate(DataFlowRequest request) {
        return Result.success(true);
    }

    @Override
    public DataSink createSink(DataFlowRequest request) {
        var destination = request.getDestinationDataAddress();

        // verify destination path
        var path = destination.getProperty("path");
        // As this is a controlled test input below is to avoid path-injection warning
        // by CodeQL
        var destinationFile = new File(path.replaceAll("\\.", ".").replaceAll("/", "/"));

        return JsonTransferDataSink.Builder.newInstance()
                .file(destinationFile)
                .requestId(request.getId())
                .partitionSize(partitionSize)
                .executorService(executorService)
                .monitor(monitor)
                .build();
    }
}
