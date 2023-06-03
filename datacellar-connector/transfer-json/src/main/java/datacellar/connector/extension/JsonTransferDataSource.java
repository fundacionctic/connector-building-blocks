package datacellar.connector.extension;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileNotFoundException;
import java.io.InputStream;
import java.util.stream.Stream;

import org.eclipse.edc.connector.dataplane.spi.pipeline.DataSource;
import org.eclipse.edc.connector.dataplane.spi.pipeline.StreamResult;
import org.eclipse.edc.spi.EdcException;

class JsonTransferDataSource implements DataSource {

    private final File file;

    JsonTransferDataSource(File file) {
        this.file = file;
    }

    @Override
    public StreamResult<Stream<Part>> openPartStream() {
        var part = new Part() {
            @Override
            public String name() {
                return file.getName();
            }

            @Override
            public InputStream openStream() {
                try {
                    return new FileInputStream(file);
                } catch (FileNotFoundException e) {
                    throw new EdcException(e);
                }
            }
        };
        return StreamResult.success(Stream.of(part));
    }
}
