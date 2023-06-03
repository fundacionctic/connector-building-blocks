package datacellar.connector.extension;

import static java.lang.String.format;
import static org.eclipse.edc.connector.dataplane.spi.pipeline.StreamFailure.Reason.GENERAL_ERROR;

import java.io.File;
import java.io.FileOutputStream;
import java.util.List;
import java.util.Objects;

import org.eclipse.edc.connector.dataplane.spi.pipeline.DataSource;
import org.eclipse.edc.connector.dataplane.spi.pipeline.StreamFailure;
import org.eclipse.edc.connector.dataplane.spi.pipeline.StreamResult;
import org.eclipse.edc.connector.dataplane.util.sink.ParallelSink;

class JsonTransferDataSink extends ParallelSink {
    private File file;

    @SuppressWarnings("deprecation")
    @io.opentelemetry.extension.annotations.WithSpan
    @Override
    protected StreamResult<Void> transferParts(List<DataSource.Part> parts) {
        for (DataSource.Part part : parts) {
            var fileName = part.name();
            try (var input = part.openStream()) {
                try (var output = new FileOutputStream(file)) {
                    try {
                        input.transferTo(output);
                    } catch (Exception e) {
                        return getTransferResult(e, "Error transferring file %s", fileName);
                    }
                } catch (Exception e) {
                    return getTransferResult(e, "Error creating file %s", fileName);
                }
            } catch (Exception e) {
                return getTransferResult(e, "Error reading file %s", fileName);
            }
        }
        return StreamResult.success();
    }

    private StreamResult<Void> getTransferResult(Exception e, String logMessage, Object... args) {
        var message = format(logMessage, args);
        monitor.severe(message, e);
        return StreamResult.failure(new StreamFailure(List.of(message), GENERAL_ERROR));
    }

    public static class Builder extends ParallelSink.Builder<Builder, JsonTransferDataSink> {

        public static Builder newInstance() {
            return new Builder();
        }

        public Builder file(File file) {
            sink.file = file;
            return this;
        }

        @Override
        protected void validate() {
            Objects.requireNonNull(sink.file, "file");
        }

        private Builder() {
            super(new JsonTransferDataSink());
        }
    }
}
