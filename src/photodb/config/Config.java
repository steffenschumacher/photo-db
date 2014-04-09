package photodb.config;

import java.io.File;
import java.io.FileNotFoundException;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Objects;
import java.util.Properties;
import java.util.logging.Level;
import java.util.logging.Logger;

/**
 *
 * @author ssch
 */
public class Config {

    private static ConfigHolder h = new ConfigHolder();
    private String libPath;
    private final ArrayList<String> scanners = new ArrayList<>();
    private long minPicSize;
    private Level logLevel;
    private String configFile;

    public static Config getInstance() throws NotInitializedException {
        return h.getINSTANCE();
    }

    public Config(String libPath, String[] scanners, long minPicSize, Level logLevel) {
        this.libPath = libPath;
        this.configFile = libPath + 
                (libPath.endsWith(File.separator) ? "" : File.separator) + 
                ".config";
        this.scanners.addAll(Arrays.asList(scanners));
        this.minPicSize = minPicSize;
        this.logLevel = logLevel;
    }

    public String getConfigFile() {
        
        return configFile;
    }

    public String getLibPath() {
        return libPath;
    }

    public String[] getScanners() {
        return scanners.toArray(new String[]{});
    }

    public long getMinPicSize() {
        return minPicSize;
    }

    public Level getLogLevel() {
        return logLevel;
    }

    protected void setConfigFile(String configFile) {
        this.configFile = configFile;
    }
    
    public void addScanner(String scanner) {
        this.scanners.add(scanner);
    }

    public void setMinPicSize(long minPicSize) {
        this.minPicSize = minPicSize;
    }

    public void setLogLevel(Level logLevel) {
        this.logLevel = logLevel;
    }
    
    

    protected Config(InputStream propertiesFile) throws FileNotFoundException, IOException {
        Properties prop = new Properties();

        try {
            //load a properties file from class path, inside static method
            prop.load(propertiesFile);

            final String pLibPath = prop.getProperty("librarypath");
            if(pLibPath == null) {
                throw new java.util.InvalidPropertiesFormatException("Missing required librarypath property");
            } else {
                this.libPath = pLibPath;
            }
            final String pLogLevel = prop.getProperty("loglevel");
            if(pLogLevel == null) {
                this.logLevel = Level.INFO;
            } else {
                this.logLevel = Level.parse(pLogLevel);
            }
            
            final String pMinPicSize = prop.getProperty("minpicsize");
            if(pMinPicSize == null) {
                this.minPicSize = 150000;   //150kb
            } else {
                long val = Long.parseLong(pMinPicSize);
                this.minPicSize = val;
            }
            final String pScannersList = prop.getProperty("scanners");
            if(pScannersList != null && !pScannersList.isEmpty()) {
                String[] pScanners = pScannersList.split("#");
                scanners.addAll(Arrays.asList(pScanners));
            }
        } finally {
            if (propertiesFile != null) {
                try {
                    propertiesFile.close();
                } catch (IOException e) {
                    Logger.getLogger(Config.class.getName()).log(Level.SEVERE, 
                            "Unable to close properties file", e);
                }
            }
        }
    }
    
    protected void storeTo(FileOutputStream propertiesFile) throws IOException {
        Properties prop = new Properties();
        prop.setProperty("librarypath", libPath);
        prop.setProperty("loglevel", logLevel.getName());
        prop.setProperty("minpicsize", String.valueOf(minPicSize));
        final StringBuilder scannersSB = new StringBuilder();
        for(String sc : getScanners()) {
            if(scannersSB.length() > 0) {
                scannersSB.append("#");
            }
            scannersSB.append(sc);
        }
        prop.setProperty("scanners", scannersSB.toString());
        prop.store(propertiesFile, null);
    }

    @Override
    public boolean equals(Object obj) {
        if(obj instanceof Config) {
            Config cObj = (Config)obj;
            return (cObj.configFile.equals(configFile) &&
                    cObj.libPath.equals(libPath) &&
                    cObj.logLevel.equals(logLevel) && 
                    cObj.minPicSize == minPicSize &&
                    cObj.scanners.equals(scanners));
        } else {
            return super.equals(obj);
        }
    }

    @Override
    public int hashCode() {
        int hash = 3;
        hash = 41 * hash + Objects.hashCode(this.libPath);
        hash = 41 * hash + Objects.hashCode(this.scanners);
        hash = 41 * hash + (int) (this.minPicSize ^ (this.minPicSize >>> 32));
        hash = 41 * hash + Objects.hashCode(this.logLevel);
        hash = 41 * hash + Objects.hashCode(this.configFile);
        return hash;
    }
    
    
}
