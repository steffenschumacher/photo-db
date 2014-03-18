
package photodb.db;

import java.sql.SQLException;
import java.util.Date;
import java.util.logging.Level;
import java.util.logging.Logger;
import org.junit.After;
import org.junit.AfterClass;
import static org.junit.Assert.*;
import org.junit.Before;
import org.junit.BeforeClass;
import org.junit.Test;
import photodb.photo.PhotoDbEntry;

/**
 *
 * @author Steffen Schumacher
 */
public class DatabaseTest {
    
    public DatabaseTest() {
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

        @Test
    public void testInsert() {
        try {
            Database db = new Database("test.db");
            PhotoDbEntry pde = new PhotoDbEntry("test.jpg", new Date(System.currentTimeMillis()), 2048, 1536, "Test camera");
            db.insert(pde);
        } catch (SQLException e) {
            Logger.getLogger(DatabaseTest.class.getName()).log(Level.SEVERE, "Couldn't initialize database", e);
        }
    }
    
    @Test
    public void testConstructor() {
        try {
            Database db = new Database("test.db");
            db.logStructure();
        } catch (SQLException e) {
            Logger.getLogger(DatabaseTest.class.getName()).log(Level.SEVERE, "Couldn't initialize database", e);
        }
    }
    
    
}
