package photodb.photo;

import com.drew.imaging.ImageProcessingException;
import java.io.FileNotFoundException;
import java.io.IOException;
import java.util.Date;
import java.util.logging.ConsoleHandler;
import java.util.logging.Handler;
import java.util.logging.Level;
import java.util.logging.Logger;
import org.junit.After;
import org.junit.AfterClass;
import org.junit.Before;
import org.junit.BeforeClass;
import org.junit.Test;
import static org.junit.Assert.*;
import photodb.log.ConsoleFormatter;

/**
 *
 * @author Steffen Schumacher
 */
public class FilePhotoTest {
    final static private String folder = "test/photodb/photo/";
    final static private Logger LOG = Logger.getLogger(FilePhotoTest.class.getName());
    
    static {
        final Level lvl = Level.ALL;
        Handler h = new ConsoleHandler();
        h.setLevel(lvl);
        h.setFormatter(new ConsoleFormatter());
        Logger.getLogger("photodb").setLevel(lvl);
        Logger.getLogger("photodb").addHandler(h);
    }
    public FilePhotoTest() {
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
     * Test of IMG_1127.jpg using class FilePhoto.
     */
    @Test
    public void testIMG1127() {
        final String img = "IMG_1127.jpg";
        System.out.println(img);
        FilePhoto instance;
        try {
            instance = new FilePhoto(folder + img);
            assertEquals(1536, instance.getHRes());
            assertEquals(2048, instance.getVRes());
            assertEquals(new Date(1117716280000L), instance.getShotDate());
            assertEquals("Canon DIGITAL IXUS 500", instance.getCamera());
        } catch (ImageProcessingException | IOException | PhotoTooSmallException ex) {
            LOG.log(Level.SEVERE, "Unhandled exception: " + ex.getMessage(), ex);
            fail("Unhandled exception: "+ex.getMessage() + ".");
        }
    }

    /**
     * Test of IMG_1127.jpg using class FilePhoto.
     */
    @Test
    public void testnr_045() {
        final String img = "nr-045.JPG";
        System.out.println(img);
        FilePhoto instance;
        try {
            dumpImg(img);
            instance = new FilePhoto(folder + img);
            assertEquals(2848, instance.getHRes());
            assertEquals(4288, instance.getVRes());
            assertEquals(new Date(1250338719000L), instance.getShotDate());
            assertEquals("NIKON D300", instance.getCamera());
        } catch (ImageProcessingException | IOException | PhotoTooSmallException ex) {
            LOG.log(Level.SEVERE, "Unhandled exception: " + ex.getMessage(), ex);
            fail("Unhandled exception: "+ex.getMessage() + ".");
        }
    }
    
    
    /**
     * Test of IMG_1127.jpg using class FilePhoto.
     */
    @Test
    public void testp1010004() {
        final String img = "p1010004.jpg";
        System.out.println(img);
        FilePhoto instance;
        try {
            dumpImg(img);
            instance = new FilePhoto(folder + img);
            assertEquals(2848, instance.getHRes());
            assertEquals(4288, instance.getVRes());
            assertEquals(new Date(1250338719000L), instance.getDate());
            assertEquals("NIKON D300", instance.getCamera());
        } catch (ImageProcessingException | IOException | PhotoTooSmallException ex) {
            LOG.log(Level.SEVERE, "Unhandled exception: " + ex.getMessage(), ex);
            fail("Unhandled exception: "+ex.getMessage() + ".");
        }
    }

        
    /**
     * Test of IMG_1127.jpg using class FilePhoto.
     */
    @Test
    public void test20131113_projektor() {
        final String img = "20131113_projektor.jpg";
        System.out.println(img);
        FilePhoto instance;
        try {
            //FilePhoto.logMetaData(folder+ img);
            instance = new FilePhoto(folder + img);
            assertEquals(680, instance.getHRes());
            assertEquals(932, instance.getVRes());
            assertEquals(new Date(1392544345000L), instance.getDate());
            assertEquals("CanoScan LiDE 210", instance.getCamera());
        } catch (ImageProcessingException | IOException | PhotoTooSmallException ex) {
            LOG.log(Level.SEVERE, "Unhandled exception: " + ex.getMessage(), ex);
            fail("Unhandled exception: "+ex.getMessage() + ".");
        }
    }
            
    /**
     * Test of IMG_1127.jpg using class FilePhoto.
     */
    @Test
    public void testmadrid001() {
        final String img = "madrid001.jpg";
        System.out.println(img);
        FilePhoto instance;
        try {
            FilePhoto.logMetaData(folder+ img);
            instance = new FilePhoto(folder + img);
            assertEquals(680, instance.getHRes());
            assertEquals(932, instance.getVRes());
            assertEquals(new Date(1392544345000L), instance.getDate());
            assertEquals("CanoScan LiDE 210", instance.getCamera());
        } catch (ImageProcessingException | IOException | PhotoTooSmallException ex) {
            LOG.log(Level.SEVERE, "Unhandled exception: " + ex.getMessage(), ex);
            fail("Unhandled exception: "+ex.getMessage() + ".");
        }
    }
    
    @Test
    public void testErrorHandling() {
        final String img = "/Volumes/HomeDisk/Billeder/Bryllup/Bryllupsrejsen/._IMG_1717.JPG";
        FilePhoto instance;
        try {
            //FilePhoto.logMetaData(img);
            instance = new FilePhoto(img);
            assertEquals(680, instance.getHRes());
            assertEquals(932, instance.getVRes());
            assertEquals(new Date(1392544345000L), instance.getDate());
            assertEquals("CanoScan LiDE 210", instance.getCamera());
        } catch (ImageProcessingException | IOException ex) {
            LOG.log(Level.SEVERE, "Unhandled exception: " + ex.getMessage(), ex);
            fail("Unhandled exception: "+ex.getMessage() + ".");
        } catch (PhotoTooSmallException ex) {
            Logger.getLogger(FilePhotoTest.class.getName()).log(Level.INFO, ex.getMessage());
        }
    }
    
    @Test
    public void testMissingTags() {
        final String img = "/Volumes/HomeDisk/Billeder/Bryllup/Bryllupsrejsen/IMG_1782.JPG";
        FilePhoto instance;
        try {
            FilePhoto.logMetaData(img);
            instance = new FilePhoto(img);
            assertEquals(1200, instance.getHRes());
            assertEquals(932, instance.getVRes());
            assertEquals(new Date(1392544345000L), instance.getDate());
            assertEquals("CanoScan LiDE 210", instance.getCamera());
        } catch (ImageProcessingException | IOException | PhotoTooSmallException ex) {
            LOG.log(Level.SEVERE, "Unhandled exception: " + ex.getMessage(), ex);
            fail("Unhandled exception: "+ex.getMessage() + ".");
        }
    }
    
    public void dumpImg(String img) {
        FilePhoto instance;
        try {
            FilePhoto.logMetaData(folder+ img);
            instance = new FilePhoto(folder + img);
            System.err.println(instance.getHRes() + "x" + instance.getVRes() + ",");
            System.err.println("D: " + instance.getShotDate() + ", " + instance.getShotDate().getTime() + ",");
            System.err.println("Camera: " + instance.getCamera());
        } catch (ImageProcessingException | IOException ex) {
            LOG.log(Level.SEVERE, "Unhandled exception: " + ex.getMessage(), ex);
            fail("Unhandled exception: "+ex.getMessage() + ".");
        } catch (PhotoTooSmallException ex) {
            Logger.getLogger(FilePhotoTest.class.getName()).log(Level.SEVERE, ex.getLocalizedMessage());
        }
    }
}
