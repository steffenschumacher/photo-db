package photodb.db;

import java.io.File;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.Date;
import java.util.logging.Level;
import java.util.logging.Logger;
import photodb.photo.Photo;
import photodb.photo.PhotoDbEntry;

/**
 * Database - short description. Detailed description.
 *
 * @author Steffen Schumacher
 * @version 1.0
 */
public class Database {

    private final static Logger LOG = Logger.getLogger(Database.class.getName());
    private final static String _SqlInsert = "insert into picture(name, shot, vRes, hRes, camera) values(?,?,?,?,?)";
    private final static String _SqlUpdName = "update picture set name = ? where shot = ? and camera = ?";
    private final static String _SqlSelect = "select name, shot, vRes, hRes, camera from picture";
    private final static String _SqlDelete = "delete from picture where shot = ? and camera = ?";

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
        try {
            File f = new File(path);
            if (f.isFile() && f.canRead() && f.canWrite()) {
                LOG.log(Level.FINE, "Attempting to initialize existing database");
                initExistingDatabase(path);
            } else if (!f.exists()) {
                LOG.log(Level.FINE, "Attempting to initialize new database");
                initNewDatabase(path);
            } else {
                LOG.log(Level.SEVERE, 
                        "Unable to open database at {0}. isFile:{1}, canRead:{2}, canWrite:{3}, exists:{4}",
                        new Object[]{path, f.isFile(), f.canRead(), f.canWrite(), f.exists()});
            }
            LOG.log(Level.FINE, "Database initialized");
                
        } catch (Exception e) {
            LOG.log(Level.SEVERE, "Unexpected exception while initing new db", e);
        }

    }

    private void initExistingDatabase(String path) throws SQLException {
        //SQLiteConfig config = new SQLiteConfig();
        connection = DriverManager.getConnection("jdbc:sqlite:" + path);
    }

    private void initNewDatabase(String path) {
        try {
            File db = new File(path);
            File dir = db.getParentFile();
            if (!dir.exists()) {
                dir.mkdirs();
            }
            // create a database connection
            initExistingDatabase(path);
            Statement statement = connection.createStatement();
            statement.setQueryTimeout(30);  // set timeout to 30 sec.
            //statement.executeUpdate("drop table if exists picture");
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
            close();
        }
    }

    public final void close() {
        try {
            if (connection != null) {
                connection.close();
            }
        } catch (SQLException e2) {
            LOG.log(Level.SEVERE, "Unexpected exception while closing db", e2);
        }
    }

    public final void insert(Photo p) throws ExistingPhotoException {
        try {
            PreparedStatement insert = connection.prepareStatement(_SqlInsert);
            insert.setString(1, p.getFileName());
            insert.setLong(2, p.getShotDate().getTime());
            insert.setInt(3, p.getVRes());
            insert.setInt(4, p.getHRes());
            insert.setString(5, p.getCamera());
            int inserted = insert.executeUpdate();
        } catch (SQLException ex) {
            if (ex.getMessage().contains("columns shot, camera are not unique")) {
                throw new ExistingPhotoException(findByDate(p.getShotDate()), p);
            } else {
                LOG.log(Level.SEVERE, "Unable to insert " + p.toString(), ex);
            }
        }
    }

    /**
     * update
     *
     * @param p Photo where shotDate must be set!!!!
     */
    public final void updateFileName(Photo p) {
        try {
            PreparedStatement update = connection.prepareStatement(_SqlUpdName);
            update.setString(1, p.getFileName());
            update.setLong(2, p.getShotDate().getTime());
            update.setString(3, p.getCamera());
            int updated = update.executeUpdate();
            if (updated != 1) {
                throw new SQLException("Error updating " + update.toString() + ", got " + updated + " updated?");
            }
        } catch (SQLException ex) {
            LOG.log(Level.SEVERE, "Unable to insert " + p.toString(), ex);

        }
    }

    /**
     * update
     *
     * @param p Photo where shotDate must be set!!!!
     */
    public final void delete(Photo p) {
        try {
            PreparedStatement delete = connection.prepareStatement(_SqlDelete);
            delete.setLong(1, p.getShotDate().getTime());
            delete.setString(2, p.getCamera());
            int deleted = delete.executeUpdate();
            if (deleted > 1) {
                throw new SQLException("Error deleting " + delete.toString() + ", got " + deleted + " deleted?");
            }
        } catch (SQLException ex) {
            LOG.log(Level.SEVERE, "Unable to insert " + p.toString(), ex);

        }
    }

    public final Photo findByDate(Date d) {
        if (d == null) {
            return null;
        }
        try {
            PreparedStatement select = connection.prepareStatement(_SqlSelect + " where shot = ?");
            select.setLong(1, d.getTime());
            ResultSet rs = select.executeQuery();
            if (rs.next()) {
                return parsePhoto(rs);
            }
        } catch (SQLException ex) {
            LOG.log(Level.SEVERE, "Unable to select by shot " + d, ex);
        }
        return null;
    }

    private final Photo parsePhoto(final ResultSet rsRow) throws SQLException {
        return (Photo) new PhotoDbEntry(
                rsRow.getString(1),
                new Date(rsRow.getLong(2)),
                rsRow.getInt(3),
                rsRow.getInt(4),
                rsRow.getString(5));
    }

    public void logStructure() {
        try {
            Statement describe = connection.createStatement();
            ResultSet rs = describe.executeQuery("select name, shot, vRes, hRes, camera from picture");
            while (rs.next()) {
                Photo p = parsePhoto(rs);
                LOG.log(Level.SEVERE, "Found: {0}", p);
            }

        } catch (SQLException ex) {
            LOG.log(Level.SEVERE, "Unable to fetch schema for picture", ex);
        }

    }
}
