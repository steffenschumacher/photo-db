package photodb.clArgs;

import java.io.File;
import java.io.FileNotFoundException;
import java.io.IOException;
import java.io.PrintStream;
import java.lang.management.ManagementFactory;
import java.util.List;
import java.util.logging.Level;
import java.util.logging.Logger;
import org.apache.commons.cli.CommandLine;
import org.apache.commons.cli.CommandLineParser;
import org.apache.commons.cli.HelpFormatter;
import org.apache.commons.cli.OptionBuilder;
import org.apache.commons.cli.Options;
import org.apache.commons.cli.ParseException;
import org.apache.commons.cli.PosixParser;
import photodb.config.Config;
import photodb.config.NotInitializedException;

/**
 *
 * @author ssch
 */
public class Parser {

    //<editor-fold defaultstate="collapsed" desc="Supported options definition">
    private static final Options _opts = new Options();

    static {
        _opts.addOption(OptionBuilder.withArgName("p")
                .withDescription("Path to where root of the storage/destination folder")
                .hasArg()
                .isRequired(false)
                .withLongOpt("Destination-path")
                .create("p"));
        _opts.addOption(OptionBuilder.withArgName("d")
                .withDescription("Loglevel [OFF|INFO|FINE|FINER|FINEST]")
                .hasArg()
                .isRequired(false)
                .withLongOpt("Level")
                .create("d"));
        _opts.addOption(OptionBuilder.withArgName("m")
                .withDescription("Minimum picturesize in kilobytes")
                .hasArg()
                .isRequired(false)
                .withLongOpt("KBs")
                .create("m"));
        _opts.addOption(OptionBuilder.withArgName("s")
                .withDescription("Source folder to scan for images")
                .hasArg()
                .isRequired(true)
                .withLongOpt("Source-path")
                .create("s"));
    }
    //</editor-fold>

    private static void printHelp(PrintStream out, final String args[]) {
        HelpFormatter formatter = new HelpFormatter();
        String commandline = "java -jar [path to jar]";
        formatter.printHelp(commandline, _opts);
    }

    public static String parseArguments(String args[]) throws IOException {
        CommandLineParser clp = new PosixParser();
        try {
            CommandLine cl = clp.parse(_opts, args, true);
            parseArguments(cl);
            //Source dir to be scanned, w/o trailing dir sep
            return cl.getOptionValue("s", ".").replace("[\\/]*$", ""); 
        } catch (ParseException ex) {
            System.err.println(ex.getMessage());
            printHelp(System.out, args);
            System.exit(0);
        }
        return null;    //Unreachable
    }

    private static void parseArguments(CommandLine cl) throws IOException {
        String root = cl.getOptionValue("p", System.getProperty("user.home")).replace("[\\/]*$", "");
        Config c = null;
        try {
            Config.getInstance();
            System.err.println("Got unexpected config before having initialized it?");
            System.exit(0);
        } catch (NotInitializedException ex) {
            try {
                c = ex.initializeConfig(Config.deriveConfigFileFromPath(root));
                ex.provideCommandLineArgs(c, cl);
            } catch (FileNotFoundException fnfe) {
                //Means we need to create one from arguments
                c = ex.initializeConfig(root, cl);
            } catch (IOException ex1) {
                Logger.getLogger(Parser.class.getName()).log(Level.SEVERE, null, ex1);
                System.exit(0);
            }
            //At this point Config should be initialized
            ex.storeConfig(c);
        }

    }

}
