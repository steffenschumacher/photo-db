/*
 * To change this license header, choose License Headers in Project Properties.
 * To change this template file, choose Tools | Templates
 * and open the template in the editor.
 */
package photodb.concurrent;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Set;
import java.util.concurrent.Future;
import java.util.concurrent.Semaphore;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;
import java.util.logging.Level;
import java.util.logging.Logger;

/**
 *
 * @author ssch
 * @param <INPUT> The object to be processed
 * @param <OUTPUT> The result of the process
 */
public abstract class BufferedExecutor<INPUT extends Object, OUTPUT extends Object> extends Thread {

    private final static Logger LOG = Logger.getLogger(BufferedExecutor.class.getName());

    //<editor-fold defaultstate="collapsed" desc="Class Job">
    protected class Job implements Future<OUTPUT> {

        private final INPUT input;
        private OUTPUT output;
        private final Semaphore jobDone = new Semaphore(0);

        public Job(INPUT input) {
            this.input = input;
        }

        @Override
        public boolean cancel(boolean mayInterruptIfRunning) {
            throw new UnsupportedOperationException("Not supported yet."); //To change body of generated methods, choose Tools | Templates.
        }

        @Override
        public boolean isCancelled() {
            return false;
        }

        @Override
        public boolean isDone() {
            return jobDone.availablePermits() > 0;
        }

        @Override
        public OUTPUT get() throws InterruptedException {
            jobDone.acquire();
            jobDone.release();
            return output;
        }

        @Override
        public OUTPUT get(long timeout, TimeUnit unit) throws InterruptedException, TimeoutException {
            if (jobDone.tryAcquire(timeout, unit)) {
                jobDone.release();
                return output;
            } else {
                throw new TimeoutException("timed out waiting for processing of " + input.toString());
            }
        }

        public void complete(OUTPUT result) {
            output = result;
            jobDone.release();
        }
    }
    //</editor-fold>

    private final int jobCapacity;
    private final int jobHoldTimeMs;
    private final Semaphore availableCapacity;
    private final Semaphore isFull = new Semaphore(0);
    private final Semaphore isRunning = new Semaphore(1);
    private final List<Job> jobQueue = new ArrayList<>();
    private final HashMap<INPUT, Job> jobMap = new HashMap<>();

    public BufferedExecutor(String name) {
        this(name, 20, 1000);
    }

    public BufferedExecutor(String name, int jobCapacity, int jobHoldTimeMs) {
        super(name);
        this.jobCapacity = jobCapacity;
        this.jobHoldTimeMs = jobHoldTimeMs;
        this.availableCapacity = new Semaphore(jobCapacity);
    }

    public BufferedExecutor() {
        this("BufferedExecutorThread", 20, 1000);
    }

    /**
     * Submits INPUT for buffered processing.
     *
     * @param job the INPUT for which OUTPUT is to be generated
     * @param timeout long
     * @param tu TimeUnit
     * @return Future < OUTPUT >
     * @throws TimeoutException thrown if the buffer (jobQueue) is full for more
     * than the timeout, preventing the job to be queued.
     * @throws InterruptedException
     */
    public Future<OUTPUT> submit(INPUT job, long timeout, TimeUnit tu) throws TimeoutException, InterruptedException {
        Job j;
        if (!availableCapacity.tryAcquire(timeout, tu)) {
            LOG.log(Level.SEVERE, "Unable to submit {0} within {1} {2} - bug?",
                    new Object[]{job.toString(), timeout, tu.toString()});
            throw new TimeoutException("Timeout for " + job.toString());
        }
        synchronized (jobQueue) {
            j = new Job(job);
            jobQueue.add(j);
            if (availableCapacity.availablePermits() == 0) {
                isFull.release();
            }
        }
        return j;
    }

    /**
     * Terminate the BufferedExecutor, by draining the semaphore.
     * 
     */
    public final void terminate() {
        isRunning.drainPermits();
    }
    
    /**
     * Run loop..
     */
    @Override
    public void run() {
        try {
            while (isRunning.availablePermits() > 0) {
                waitAndExecuteOnBufferedJobs();
            }
        } catch (InterruptedException e) {
            //Execution is likely done..
        }
        LOG.log(Level.FINER, "Cleaning up {0}", this.getClass().getSimpleName());

    }

    /**
     * Main process of the thread, called over and over again. It waits for
     * jobQueue to reach its capacity, or up to requestHoldTimeMs. Then
     * housekeeping is performed before calling the abstract executeJobs().
     * Finally the jobMap is checked for leftover Jobs which neglected to be
     * completed.
     *
     * @throws InterruptedException
     */
    protected void waitAndExecuteOnBufferedJobs() throws InterruptedException {
        //Wait until full or for requestHoldTimeMs whichever comes first
        if (!isFull.tryAcquire(jobHoldTimeMs, TimeUnit.MILLISECONDS)) {
            availableCapacity.drainPermits(); //no more requests for now..
        }

        performHouseKeeping();
        if (jobMap.isEmpty()) {
            //No need to continue
            LOG.log(Level.FINER,
                    "{0} didn't receive any jobs for {1} ms - skipping execution",
                    new Object[]{this.getClass().getName(), jobHoldTimeMs});
        } else {
            executeJobs();
            for (Job deadJob : jobMap.values()) {
                LOG.log(Level.SEVERE, "The job for {0} failed to yield any results - returning null", deadJob.input);
                completeJob(deadJob.input, null);
            }
        }
    }

    /**
     * Move all Jobs from the jobQueue to the jobMap, and open up for new
     * requests..
     */
    protected void performHouseKeeping() {
        synchronized (jobQueue) {
            //move all jobs to the map..
            for (Job rq : jobQueue) {
                jobMap.put(rq.input, rq);
            }
            jobQueue.clear();
        }
        //Prepare for the next round of requests, and open shop..
        availableCapacity.release(jobCapacity);
    }

    protected Set<INPUT> getInputs() {
        return jobMap.keySet();
    }

    /**
     * Inserts the resulting output for the given input, and signals the Job
     * object that it is done.
     *
     * @param key the INPUT
     * @param result the OUTPUT
     */
    protected void completeJob(INPUT key, OUTPUT result) {
        if (!jobMap.containsKey(key)) {
            LOG.log(Level.SEVERE, "Possible bug - couldn't find job for {0} in requestMap?", key.toString());
        } else {
            Job j = jobMap.remove(key);
            j.complete(result);
        }
    }

    /**
     * The implementation of this abstract method must process/execute all jobs,
     * and subsequently call completeJob(INPUT, OUTPUT) for each Job. This
     * ensures that the Future objects (implemented by class Job) actually gets
     * signaled once the output of the job is available. Each job is
     * subsequently completed as required
     */
    protected abstract void executeJobs();
}
