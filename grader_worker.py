from rq import Worker, Queue, Connection
from rq.job import JobStatus
from grader.__init__ import conn, grader_queue

listen = ['grader']

MAX_RETRY = 10


def retry_handler(job):
    """ An exception handler that requeues exceptions MAX_RETRY number of times """
    job.meta.setdefault('failures', 0)
    job.meta['failures'] += 1
    if job.meta['failures'] >= MAX_RETRY:
        job.save()
        return True
    print("Job Failed! Now retrying attempt ({0})".format(job.meta['failures']))
    job.status = JobStatus.QUEUED
    grader_queue.enqueue_job(job)
    return False


if __name__ == '__main__':
    with Connection(conn):
        worker = Worker(list(map(Queue, listen)))
        worker.push_exc_handler(retry_handler)
        try:
            worker.work()
        except Exception as e:
            raise Exception("Error starting worker. Make sure redis-server is running.")
