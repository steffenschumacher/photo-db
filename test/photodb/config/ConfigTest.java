package photodb.config;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.util.logging.Level;
import java.util.logging.Logger;
import org.junit.After;
import org.junit.AfterClass;
import static org.junit.Assert.*;
import org.junit.Before;
import org.junit.BeforeClass;
import org.junit.Test;

/**
 *
 * @author ssch
 */
public class ConfigTest {
    
    public ConfigTest() {
    }
    
    @BeforeClass
    public static void setUpClass() {
    }
    
    @AfterClass
    public static void tearDownClass() {
    }
    
    @Before
    public void setUp() {
    }
    
    @After
    public void tearDown() {
    }

    /**
     * Test of getInstance method, of class Config.
     */
    @Test
    public void testGetInstanceAndCreate() throws Exception {
        System.out.println("testGetInstanceAndCreate");
        Config expResult = new Config("/tmp/", new String[]{"sc1", "sc2", "sc3"}, 150000L, Level.FINEST);
        File cfgFile = new File(expResult.getConfigFile());
        try {
            Config result = Config.getInstance();
            fail("We should not have a config initialized yet!");
        } catch (NotInitializedException e) {
            e.initializeConfig(expResult);
            Config result = Config.getInstance();
            assertEquals(expResult, result);
            assertTrue(cfgFile.canRead());
            cfgFile.delete();
        }
    }

    /**
     * Test of getConfigFile method, of class Config.
     */
    @Test
    public void testReadConfigFile() {
        System.out.println("testReadConfigFile");
        Config expResult = new Config("/tmp/", new String[]{"sc1", "sc2", "sc3"}, 150000L, Level.FINEST);
        File cfgFile = new File(expResult.getConfigFile());
        try {
            expResult.storeTo(new FileOutputStream(cfgFile));
        } catch (IOException ex) {
            fail("Unable to store configuration file at " + expResult.getConfigFile());
        }
        try {
            Config result = Config.getInstance();
            fail("We should not have a config initialized yet!");
        } catch (NotInitializedException e) {
            try {
                e.initializeConfig(expResult.getConfigFile());
                Config result = Config.getInstance();
                assertEquals(expResult, result);
                cfgFile.delete();
            } catch (IOException ex) {
                fail("Unable to read/parse configuration file?");
            } catch (NotInitializedException ex) {
                fail("This time it should have been initialized");
            }
        }
    }

    /**
     * Test of getLibPath method, of class Config.
     */
    @Test
    public void testGetLibPath() {
        System.out.println("getLibPath");
        Config instance = null;
        String expResult = "";
        String result = instance.getLibPath();
        assertEquals(expResult, result);
        // TODO review the generated test code and remove the default call to fail.
        fail("The test case is a prototype.");
    }

    /**
     * Test of getScanners method, of class Config.
     */
    @Test
    public void testGetScanners() {
        System.out.println("getScanners");
        Config instance = null;
        String[] expResult = null;
        String[] result = instance.getScanners();
        assertArrayEquals(expResult, result);
        // TODO review the generated test code and remove the default call to fail.
        fail("The test case is a prototype.");
    }

    /**
     * Test of getMinPicSize method, of class Config.
     */
    @Test
    public void testGetMinPicSize() {
        System.out.println("getMinPicSize");
        Config instance = null;
        long expResult = 0L;
        long result = instance.getMinPicSize();
        assertEquals(expResult, result);
        // TODO review the generated test code and remove the default call to fail.
        fail("The test case is a prototype.");
    }

    /**
     * Test of getLogLevel method, of class Config.
     */
    @Test
    public void testGetLogLevel() {
        System.out.println("getLogLevel");
        Config instance = null;
        Level expResult = null;
        Level result = instance.getLogLevel();
        assertEquals(expResult, result);
        // TODO review the generated test code and remove the default call to fail.
        fail("The test case is a prototype.");
    }

    /**
     * Test of setConfigFile method, of class Config.
     */
    @Test
    public void testSetConfigFile() {
        System.out.println("setConfigFile");
        String configFile = "";
        Config instance = null;
        instance.setConfigFile(configFile);
        // TODO review the generated test code and remove the default call to fail.
        fail("The test case is a prototype.");
    }

    /**
     * Test of addScanner method, of class Config.
     */
    @Test
    public void testAddScanner() {
        System.out.println("addScanner");
        String scanner = "";
        Config instance = null;
        instance.addScanner(scanner);
        // TODO review the generated test code and remove the default call to fail.
        fail("The test case is a prototype.");
    }

    /**
     * Test of setMinPicSize method, of class Config.
     */
    @Test
    public void testSetMinPicSize() {
        System.out.println("setMinPicSize");
        long minPicSize = 0L;
        Config instance = null;
        instance.setMinPicSize(minPicSize);
        // TODO review the generated test code and remove the default call to fail.
        fail("The test case is a prototype.");
    }

    /**
     * Test of setLogLevel method, of class Config.
     */
    @Test
    public void testSetLogLevel() {
        System.out.println("setLogLevel");
        Level logLevel = null;
        Config instance = null;
        instance.setLogLevel(logLevel);
        // TODO review the generated test code and remove the default call to fail.
        fail("The test case is a prototype.");
    }
    
}
