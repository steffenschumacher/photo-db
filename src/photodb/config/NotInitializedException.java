package photodb.config;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileNotFoundException;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.util.logging.Level;
import org.apache.commons.cli.CommandLine;

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
    public Config initializeConfig(String proportiesFile) throws FileNotFoundException, IOException {
        File f = new File(proportiesFile);
        if(f.isFile() && f.canRead()) {
            InputStream input = new FileInputStream(f);
            Config instance = new Config(input);
            instance.setConfigFile(proportiesFile);
            ch.instantiateConfig(instance);
            return instance;
        } else {
            throw new FileNotFoundException("Unable to read file: " + f);
        }
    }
    /**
     * initializeConfig initializes config to provided object
     * @param c 
     */
    public void initializeConfig(Config c) {
        ch.instantiateConfig(c);
    }
    
    public Config initializeConfig(String path, CommandLine cl) {
        Config c = Config.createFromArgs(path, cl);
        ch.instantiateConfig(c);
        return c;
    }
    
    /**
     * provideCommandLineArgs
     * @param c
     * @param cl 
     */
    public void provideCommandLineArgs(Config c, CommandLine cl) {
        if(cl.hasOption("m")) {
            c.setMinPicSize(Long.parseLong(cl.getOptionValue("m")));
        }
        if(cl.hasOption("d")) {
            c.setLogLevel(Level.parse(cl.getOptionValue("d")));
        }
    }
    /**
     * storeConfig
     * @param c
     * @throws IOException 
     */
    public void storeConfig(Config c) throws IOException {
        /*
                File rootDir = new File(root);
        if(!rootDir.exists()) {
            rootDir.mkdirs();
        } else if(!rootDir.isDirectory()) {
            throw new IllegalArgumentException("The folder " + root + " already exists, and isn't a folder");
        } else if(!rootDir.canWrite() || !rootDir.canRead()) {
            throw new IOException("The folder " + root + " has insufficient permissions");
        }
        //Ok, so now the root dir is established..
        */
        File newPropertiesFile = new File(c.getConfigFile());
        FileOutputStream fos = new FileOutputStream(newPropertiesFile);
        c.storeTo(fos);
    }
}
