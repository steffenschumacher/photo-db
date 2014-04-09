package photodb.config;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileNotFoundException;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;

/**
 *
 * @author ssch
 */
public class NotInitializedException extends Exception {

    private final ConfigHolder ch;

    /**
     * Creates a new instance of <code>NotInitializedException</code> without
     * detail message.
     *
     * @param ch
     */
    protected NotInitializedException(final ConfigHolder ch) {
        this.ch = ch;
    }

    /**
     * Constructs an instance of <code>NotInitializedException</code> with the
     * specified detail message.
     *
     * @param msg the detail message.
     * @param ch
     */
    protected NotInitializedException(String msg, final ConfigHolder ch) {
        super(msg);
        this.ch = ch;
    }
    
    /**
     * initializeConfig attempts to parse config from a file in the classpath
     * @throws FileNotFoundException
     * @throws IOException 
     */
    public void initializeConfig() throws FileNotFoundException, IOException {
        String filename = "config.properties";
        InputStream input = photodb.PhotoDb.class.getClassLoader().getResourceAsStream(filename);
        if (input == null) {
            throw new FileNotFoundException();
        }
        ch.instantiateConfig(new Config(input));
    }
    
    /**
     * initializeConfig attempts to parse config from provided file;
     * @param proportiesFile
     * @throws FileNotFoundException
     * @throws IOException 
     */
    public void initializeConfig(String proportiesFile) throws FileNotFoundException, IOException {
        File f = new File(proportiesFile);
        if(f.isFile() && f.canRead()) {
            InputStream input = new FileInputStream(f);
            Config instance = new Config(input);
            instance.setConfigFile(proportiesFile);
            ch.instantiateConfig(instance);
        } else {
            throw new FileNotFoundException("Unable to read file: " + f);
        }
    }
    /**
     * initializeConfig initializes config to provided object
     * @param c 
     * @throws java.io.IOException if we cannot store the properties file
     */
    public void initializeConfig(Config c) throws IOException {
        ch.instantiateConfig(c);
        File newPropertiesFile = new File(c.getConfigFile());
        FileOutputStream fos = new FileOutputStream(newPropertiesFile);
        c.storeTo(fos);
    }
}
