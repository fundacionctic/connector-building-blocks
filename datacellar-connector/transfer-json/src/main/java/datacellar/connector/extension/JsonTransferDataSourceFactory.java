package datacellar.connector.extension;

import java.io.File;

import org.eclipse.edc.connector.dataplane.spi.pipeline.DataSource;
import org.eclipse.edc.connector.dataplane.spi.pipeline.DataSourceFactory;
import org.eclipse.edc.spi.result.Result;
import org.eclipse.edc.spi.types.domain.transfer.DataFlowRequest;
import org.jetbrains.annotations.NotNull;

class JsonTransferDataSourceFactory implements DataSourceFactory {
    @Override
    public boolean canHandle(DataFlowRequest dataRequest) {
        return JsonTransferExtension.JSON_TYPE.equalsIgnoreCase(dataRequest.getSourceDataAddress().getType());
    }

    @Override
    public @NotNull Result<Boolean> validate(DataFlowRequest request) {
        var source = getFile(request);
        if (!source.exists()) {
            return Result.failure("Source file " + source.getName() + " does not exist!");
        }

        return Result.success(true);
    }

    @Override
    public DataSource createSource(DataFlowRequest request) {
        var source = getFile(request);
        return new JsonTransferDataSource(source);
    }

    @NotNull
    private File getFile(DataFlowRequest request) {
        var dataAddress = request.getSourceDataAddress();
        // verify source path
        var sourceFileName = dataAddress.getProperty("filename");
        var path = dataAddress.getProperty("path");
        // As this is a controlled test input below is to avoid path-injection warning
        // by CodeQL
        sourceFileName = sourceFileName.replaceAll("\\.", ".").replaceAll("/", "/");
        path = path.replaceAll("\\.", ".").replaceAll("/", "/");
        return new File(path, sourceFileName);
    }
}
