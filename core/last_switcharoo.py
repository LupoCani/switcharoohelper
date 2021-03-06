import prawcore.exceptions

LIMIT = 10

class Switcharoo:
    def __init__(self, thread_id, comment_id, comment_url, submission_url, submission_id, submission=None):
        self.thread_id = thread_id
        self.comment_id = comment_id
        self.comment_url = comment_url
        self.submission_url = submission_url
        self.submission = submission
        self.submission_id = submission_id

    """Support for deprecated access"""
    def __getitem__(self, item):
        self.__getattribute__(item)

    def __str__(self):
        return self.submission_id

    def save(self):
        return {"thread_id": self.thread_id, "comment_id": self.comment_id, "comment_url": self.comment_url,
                "submission_url": self.submission_url, "submission_id": self.submission_id}

def DictToSwitcharoo(properties):
    return Switcharoo(properties["thread_id"], properties["comment_id"], properties["comment_url"],
                      properties["submission_url"], properties["submission_id"])

class SwitcharooLog:
    """Keeps a log of the switcharoos, both good/verified and the last one
    in general. Used to give correct links and to find place in submissions log"""
    def __init__(self, reddit, load=None):
        """

        :param reddit: PRAW Reddit instance
        :param load: Data from save() to resume object
        """
        self.reddit = reddit

        if load:
            self._good_roos = []
            for i in load["good_roos"]:
                self._good_roos.append(DictToSwitcharoo(i))
            self._last_roos = load["last_roos"]
        else:
            self._good_roos = []
            self._last_roos = []

    def verify(self):
        """Check that if the last good or last submitted roo was deleted (by someone else), we don't link to it"""
        # Track the indices to remove
        remove = []
        for i, roo in enumerate(self._good_roos):
            submission = self.reddit.submission(roo.submission_id)
            try:
                if submission.author is None:
                    remove.append(i)
                    continue
                if submission.banned_by:
                    if not submission.approved_by:
                        remove.append(i)
                        continue
                if hasattr(submission, "removed"):
                    if submission.removed:
                        remove.append(i)
                        continue
                break   # This one passed the test, we are done here
            except prawcore.exceptions.BadRequest:  # Failed request also indicates removed post
                remove.append(i)

        for i in sorted(remove, reverse=True):  # Work backwards to avoid updating indexes
            del self._good_roos[i]

        remove = []     # This may not be a good idea since a roo may have linked to a deleted one of these
        for i, roo in enumerate(self._last_roos):
            submission = self.reddit.submission(url=roo)
            try:
                if submission.author is None:
                    remove.append(i)
                    continue
                if submission.banned_by:
                    if not submission.approved_by:
                        remove.append(i)
                        continue
                if hasattr(submission, "removed"):
                    if submission.removed:
                        remove.append(i)
                        continue
                break   # This one passed the test, we are done here
            except prawcore.exceptions.BadRequest:  # Failed request also indicates removed post
                remove.append(i)

        for i in sorted(remove, reverse=True):  # Work backwards to avoid updating indexes
            del self._last_roos[i]

    def verify_settled(self):
        """Verify roos for linking on the tail of the roo log. We need at least one good one for linking to"""
        # Track the indicies to remove
        remove = []
        for i, roo in enumerate(reversed(self._good_roos)):
            # reverse the index since we are reading backwards
            index = len(self._good_roos) - 1 - i
            submission = self.reddit.submission(url=roo["submission_url"])
            try:
                if submission.author is None:
                    remove.append(index)
                elif hasattr(submission, "removed"):
                    if submission.removed:
                        remove.append(index)
                else:  # We only need one good submission to continue
                    break
            except prawcore.exceptions.BadRequest:  # Failed request also indicates removed post
                remove.append(index)

        for i in sorted(remove, reverse=True):  # Work backwards to avoid updating indexes
            del self._good_roos[index]

        remove = []
        for i, roo in enumerate(reversed(self._last_roos)):
            # reverse the index since we are reading backwards
            index = len(self._good_roos) - 1 - i
            submission = self.reddit.submission(url=roo)
            if submission.author is None:
                remove.append(index)
            elif hasattr(submission, "removed"):
                if submission.removed:
                    remove.append(index)
            else:  # We only need one good submission to continue
                break
        for i in sorted(remove, reverse=True):  # Work backwards to avoid updating indexes
            del self._last_roos[index]



    def add_good(self, submission, thread_id, comment_id):
        """
    
        :param submission: submission dictionary
        :param thread_id: id of the switcharoo comment thread
        :param comment_id: id of the switcharoo comment
        :return: 
        """
        self._good_roos.insert(0, Switcharoo(thread_id, comment_id, submission.url,
                                             "https://reddit.com{}".format(submission.permalink), submission.id,
                                             submission))

        # Remove any excess roos
        if len(self._good_roos) > LIMIT:
            del self._good_roos[len(self._good_roos) - 1]

    def add_last(self, submission_url):
        self._last_roos.insert(0, submission_url)

        # Remove any excess roos
        if len(self._last_roos) > LIMIT:
            del self._last_roos[len(self._last_roos)-1]

    def last_good(self, index=0):
        if self._good_roos:
            return self._good_roos[index]
        else:
            return None

    def last_submitted(self, index=0):
        if self._last_roos:
            return self._last_roos[index]
        else:
            return None

    def save(self):
        """Returns object ready for jsonification"""
        good_roos = []
        for i in self._good_roos:
            good_roos.append(i.save())
        return {"good_roos": good_roos, "last_roos": self._last_roos}
