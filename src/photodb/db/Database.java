package photodb.db;

import java.io.File;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.logging.Level;
import java.util.logging.Logger;

/**
 * Database - short description. Detailed description.
 *
 * @author Steffen Schumacher
 * @version 1.0
 */
public class Database {

    private final static Logger LOG = Logger.getLogger(Database.class.getName());

    static {
        try {
            // load the sqlite-JDBC driver using the current class loader
            Class.forName("org.sqlite.JDBC");
        } catch (ClassNotFoundException ex) {
            LOG.log(Level.SEVERE, "Unable to load sqlite drivers?", ex);
        }
    }
    Connection connection = null;

    public Database(String path) throws SQLException {

        File f = new File(path);
        if (f.isFile() && !f.canRead() && f.canWrite()) {
            initExistingDatabase(path);
        } else if (!f.exists() && f.getParentFile().canWrite()) {
            initNewDatabase(path);
        }

    }
    
    private void initExistingDatabase(String path) throws SQLException {
        //SQLiteConfig config = new SQLiteConfig();
        connection = DriverManager.getConnection("jdbc:sqlite:" + path);
    }

    private void initNewDatabase(String path) {
        try {
            // create a database connection
            initExistingDatabase(path);
            Statement statement = connection.createStatement();
            statement.setQueryTimeout(30);  // set timeout to 30 sec.
            statement.executeUpdate("drop table if exists picture");
            statement.executeUpdate("create table picture ("
                    + "id int primary key, "
                    + "name varchar(80) not null, "
                    + "shot int not null, "
                    + "vRes int not null,"
                    + "hRes int not null,"
                    + "camera varchar(150) not null)");
            statement.executeUpdate("create UNIQUE INDEX date_cam on picture (shot, camera)");
            statement.executeUpdate("create INDEX camera on picture (camera)");
        } catch (SQLException e) {
            LOG.log(Level.SEVERE, "Unexpected exception while initing new db", e);
        } finally {
            try {
                if (connection != null) {
                    connection.close();
                }
            } catch (SQLException e) {
                LOG.log(Level.SEVERE, "Unexpected exception while closing db", e);
            }
        }
    }

}
