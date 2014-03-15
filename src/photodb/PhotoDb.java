package photodb;

import java.util.Enumeration;
import java.util.logging.LogManager;

/**
 *
 * @author Steffen Schumacher
 */
public class PhotoDb {

    /**
     * @param args the command line arguments
     */
    public static void main(String[] args) {
        LogManager lm = LogManager.getLogManager();
        Enumeration<String> loggerNames = lm.getLoggerNames();
        while(loggerNames.hasMoreElements()) {
            String name = loggerNames.nextElement();
            System.out.println("Found logger " + name);
        }
        final String searchPath = "/Users/ssch/Pictures";
        
    }
    
}
