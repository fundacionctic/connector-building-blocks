package eu.datacellar.connector;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.List;

import org.eclipse.edc.crawler.spi.TargetNode;
import org.eclipse.edc.crawler.spi.TargetNodeDirectory;
import org.json.JSONArray;
import org.json.JSONObject;

/**
 * Implementation of TargetNodeDirectory that provides a directory of catalog
 * nodes.
 * This class manages the list of target nodes that the federated catalog
 * crawler will access.
 * The nodes are loaded from a JSON configuration file specified by the
 * catalogNodesConfigPath.
 */
public class CatalogNodeDirectory implements TargetNodeDirectory {
    /**
     * List of target nodes loaded from the configuration
     */
    private final List<TargetNode> nodes;

    /**
     * Path to the JSON configuration file containing catalog nodes information.
     * May be null if no configuration file is provided.
     */
    private final String catalogNodesConfigPath;

    /**
     * Creates a new CatalogNodeDirectory instance
     *
     * @param catalogNodesConfigPath Path to the JSON configuration file containing
     *                               catalog nodes information. May be null.
     */
    public CatalogNodeDirectory(String catalogNodesConfigPath) {
        this.nodes = new ArrayList<>();
        this.catalogNodesConfigPath = catalogNodesConfigPath;

        if (catalogNodesConfigPath != null) {
            loadNodesFromConfig();
        }
    }

    /**
     * Loads the catalog nodes from the JSON configuration file.
     * The configuration file should contain a "nodes" array with each node having:
     * - protocolVersions: array of supported protocol versions
     * - id: unique identifier for the node
     * - url: endpoint URL of the node
     * - protocolSpecification: specification URL for the protocol
     *
     * @throws RuntimeException if there is an error reading or parsing the
     *                          configuration file
     */
    private void loadNodesFromConfig() {
        try {
            String jsonContent = Files.readString(Paths.get(catalogNodesConfigPath));
            JSONObject config = new JSONObject(jsonContent);
            JSONArray nodesArray = config.getJSONArray("nodes");

            for (int i = 0; i < nodesArray.length(); i++) {
                JSONObject nodeConfig = nodesArray.getJSONObject(i);

                List<String> protocols = nodeConfig.getJSONArray("protocolVersions").toList().stream()
                        .map(Object::toString)
                        .toList();

                nodes.add(new TargetNode(
                        nodeConfig.getString("protocolSpecification"),
                        nodeConfig.getString("id"),
                        nodeConfig.getString("url"),
                        protocols));
            }
        } catch (IOException e) {
            throw new RuntimeException("Failed to load catalog nodes configuration", e);
        }
    }

    /**
     * Returns all target nodes loaded from the configuration
     *
     * @return List of all configured TargetNode instances
     */
    @Override
    public List<TargetNode> getAll() {
        return nodes;
    }

    /**
     * Adds a new target node to the directory
     *
     * @param targetNode The TargetNode instance to add
     */
    @Override
    public void insert(TargetNode targetNode) {
        nodes.add(targetNode);
    }
}