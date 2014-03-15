package photodb.photo;

import java.awt.Image;
import java.awt.image.BufferedImage;
import org.junit.After;
import org.junit.AfterClass;
import org.junit.Before;
import org.junit.BeforeClass;
import org.junit.Test;
import static org.junit.Assert.*;
import static photodb.photo.ImageCompare.saveJPG;

/**
 *
 * @author Steffen Schumacher
 */
public class ImageCompareTest {
    final String folder = "test/photodb/photo/";
    public ImageCompareTest() {
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
     * Test of autoSetParameters method, of class ImageCompare.
     */
    @Test
    public void testCompareWithLowRes() {
        System.out.println("testCompareWithLowRes");
        final String jpeg = "IMG_1127";
        
        // Create a compare object specifying the 2 images for comparison.
        ImageCompare ic = new ImageCompare(folder + jpeg + ".jpg", folder + jpeg + "_reduced.jpg");
	// Set the comparison parameters. 
        //   (num vertical regions, num horizontal regions, sensitivity, stabilizer)
        ic.setParameters(8, 6, 5, 10);
        // Display some indication of the differences in the image.
        ic.setDebugMode(0);
        // Compare.
        ic.compare();
        
        // If its not a match then write a file to show changed regions.
        if (!ic.match()) {
            saveJPG(ic.getChangeIndicator(), folder + jpeg + "_differences.jpg");
            fail("Unexpected differences, stored in " + jpeg + "_differences.jpg");
        }
    }
    
        /**
     * Test of autoSetParameters method, of class ImageCompare.
     */
    @Test
    public void testCompareWithRect() {
        System.out.println("testCompareWithRect");
        final String jpeg = "IMG_1127";
        
        // Create a compare object specifying the 2 images for comparison.
        ImageCompare ic = new ImageCompare(folder + jpeg + ".jpg", folder + jpeg + "_rect.jpg");
	// Set the comparison parameters. 
        //   (num vertical regions, num horizontal regions, sensitivity, stabilizer)
        ic.setParameters(24, 18, 1, 10);
        // Display some indication of the differences in the image.
        ic.setDebugMode(0);
        // Compare.
        ic.compare();
        
        // If its not a match then write a file to show changed regions.
        if (ic.match()) {
            fail("Expecting differences but none found");
        } else {
            saveJPG(ic.getChangeIndicator(), folder + jpeg + "_differences.jpg");
        }
    }

}
