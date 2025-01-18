package eu.datacellar.connector;

import java.nio.file.Paths;

import org.eclipse.edc.crawler.spi.TargetNodeDirectory;
import org.eclipse.edc.runtime.metamodel.annotation.Extension;
import org.eclipse.edc.runtime.metamodel.annotation.Provider;
import org.eclipse.edc.runtime.metamodel.annotation.Setting;
import org.eclipse.edc.spi.monitor.Monitor;
import org.eclipse.edc.spi.system.ServiceExtension;
import org.eclipse.edc.spi.system.ServiceExtensionContext;

/**
 * Extension that provides a directory of catalog nodes for the federated
 * catalog crawler.
 * This extension initializes and registers the CatalogNodeDirectory which
 * maintains
 * the list of target nodes that will be crawled.
 */
@Extension(value = CatalogNodeDirectoryExtension.NAME)
public class CatalogNodeDirectoryExtension implements ServiceExtension {
    private static final String EDC_FS_CONFIG = "edc.fs.config";

    private ServiceExtensionContext context;

    /**
     * The name of the extension.
     */
    public static final String NAME = "Federated Catalog Launcher";

    @Setting
    private static final String CATALOG_NODES_CONFIG = "es.ctic.catalog.nodes.config";

    /**
     * Provides the TargetNodeDirectory implementation that will be used by the
     * federated catalog crawler.
     * 
     * @return A new instance of CatalogNodeDirectory
     */
    @Provider
    public TargetNodeDirectory federatedCacheNodeDirectory() {
        Monitor monitor = context.getMonitor();

        String catalogNodesConfigPath = context.getSetting(CATALOG_NODES_CONFIG, null);

        if (catalogNodesConfigPath != null && !Paths.get(catalogNodesConfigPath).isAbsolute()) {
            monitor.info(String.format(
                    "Catalog nodes configuration path (%s) is not absolute, resolving relative to properties path",
                    catalogNodesConfigPath));

            String propertiesPath = System.getProperty(EDC_FS_CONFIG);

            if (propertiesPath == null) {
                throw new IllegalArgumentException(String.format(
                        "Cannot resolve catalog nodes configuration path (%s) relative to properties path (%s)",
                        catalogNodesConfigPath, propertiesPath));
            }

            catalogNodesConfigPath = Paths.get(propertiesPath).getParent().resolve(catalogNodesConfigPath)
                    .toString();
        }

        if (catalogNodesConfigPath == null) {
            monitor.warning(String.format("Catalog nodes configuration path (%s) is not set",
                    CATALOG_NODES_CONFIG));
        }

        monitor.info(String.format("Catalog nodes configuration path: %s", catalogNodesConfigPath));

        return new CatalogNodeDirectory(catalogNodesConfigPath);
    }

    /**
     * Initializes the extension.
     * 
     * @param context The service extension context containing runtime services and
     *                configurations
     */
    @Override
    public void initialize(ServiceExtensionContext context) {
        this.context = context;
        Monitor monitor = context.getMonitor();
        monitor.info(String.format("Initialized extension: %s", this.getClass().getName()));
    }
}