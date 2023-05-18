package datacellar.connector.extension;

import org.eclipse.edc.connector.dataplane.spi.pipeline.DataSource;
import org.eclipse.edc.spi.EdcException;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileNotFoundException;
import java.io.InputStream;
import java.util.stream.Stream;

class JsonTransferDataSource implements DataSource {

    private final File file;

    JsonTransferDataSource(File file) {
        this.file = file;
    }

    @Override
    public Stream<Part> openPartStream() {
        return Stream.of(new Part() {
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
        });
    }
}
