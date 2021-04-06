#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This is a pure Python implementation of the [rsync algorithm] [TM96].

Updated to use SHA256 hashing (instead of the standard implementation
which uses outdated MD5 hashes), and packages for disutils 
distribution by Isis Lovecruft, <isis@patternsinthevoid.net>. The
majority of the code is blatantly stolen from Eric Pruitt's code
as posted on [ActiveState] [1].

[1]: https://code.activestate.com/recipes/577518-rsync-algorithm/

[TM96]: Andrew Tridgell and Paul Mackerras. The rsync algorithm.
Technical Report TR-CS-96-05, Canberra 0200 ACT, Australia, 1996.
http://samba.anu.edu.au/rsync/.

### Example Use Case: ###

    # On the system containing the file that needs to be patched
    >>> unpatched = open("unpatched.file", "rb")
    >>> hashes = blockchecksums(unpatched)

    # On the remote system after having received `hashes`
    >>> patchedfile = open("patched.file", "rb")
    >>> delta = rsyncdelta(patchedfile, hashes)

    # System with the unpatched file after receiving `delta`
    >>> unpatched.seek(0)
    >>> save_to = open("locally-patched.file", "wb")
    >>> patchstream(unpatched, save_to, delta)
"""

import collections
import hashlib

__all__ = ["rollingchecksum", "weakchecksum", "patchstream", "rsyncdelta",
           "blockchecksums", "gene_blockchecksums"]


def rsyncdelta(datastream, remotesignatures, blocksize=4096):
    """
    Generates a binary patch when supplied with the weak and strong
    hashes from an unpatched target and a readable stream for the
    up-to-date data. The blocksize must be the same as the value
    used to generate remotesignatures.
    """
    remote_weak = list()
    remote_strong = list()

    for sig in remotesignatures:
        remote_weak.append(int(sig[0]))
        remote_strong.append(sig[1])

    match = True
    matchblock = -1
    deltaqueue = collections.deque()

    while True:
        if match and datastream is not None:
            # Whenever there is a match or the loop is running for the first
            # time, populate the window using weakchecksum instead of rolling
            # through every single byte which takes at least twice as long.
            window = collections.deque(bytes(datastream.read(blocksize)))
            checksum, a, b = weakchecksum(window)

        try:
            # If there are two identical weak checksums in a file, and the
            # matching strong hash does not occur at the first match, it will
            # be missed and the data sent over. May fix eventually, but this
            # problem arises very rarely.
            matchblock = remote_weak.index(checksum, matchblock + 1)
            stronghash = hashlib.sha256(bytes(window)).hexdigest()
            matchblock = remote_strong.index(stronghash, matchblock)

            match = True
            deltaqueue.append(matchblock)

            if datastream.closed:
                break
            continue

        except ValueError:
            # The weakchecksum did not match
            match = False
            try:
                if datastream:
                    # Get the next byte and affix to the window
                    newbyte = ord(datastream.read(1))
                    window.append(newbyte)
            except TypeError:
                # No more data from the file; the window will slowly shrink.
                # newbyte needs to be zero from here on to keep the checksum
                # correct.
                newbyte = 0
                tailsize = datastream.tell() % blocksize
                datastream = None

            if datastream is None and len(window) <= tailsize:
                # The likelihood that any blocks will match after this is
                # nearly nil so call it quits.
                deltaqueue.append(window)
                break

            # Yank off the extra byte and calculate the new window checksum
            oldbyte = window.popleft()
            checksum, a, b = rollingchecksum(oldbyte, newbyte, a, b, blocksize)

            # Add the old byte the file delta. This is data that was not found
            # inside of a matching block so it needs to be sent to the target.
            try:
                deltaqueue[-1].append(oldbyte)
            except (AttributeError, IndexError):
                deltaqueue.append([oldbyte])

    # Return a delta that starts with the blocksize and converts all iterables
    # to bytes.
    deltastructure = [blocksize]
    for element in deltaqueue:
        if isinstance(element, int):
            deltastructure.append(element)
        elif element:
            deltastructure.append(bytes(element))

    return deltastructure


def blockchecksums(instream, blocksize=4096):
    """
    Returns a list of weak and strong hashes for each block of the
    defined size for the given data stream.
    """
    weakhashes = list()
    stronghashes = list()
    read = instream.read(blocksize)

    while read:
        weakhashes.append(weakchecksum(bytes(read))[0])
        stronghashes.append(hashlib.sha256(read).hexdigest())
        read = instream.read(blocksize)

    return weakhashes, stronghashes


def gene_blockchecksums(instream, blocksize=4096):
    """
    yield a list of weak and strong hashes for each block of the
    defined size for the given data stream.
    """
    read = instream.read(blocksize)

    while read:
        weakhash = weakchecksum(bytes(read))[0]
        stronghash = hashlib.sha256(read).hexdigest()
        yield ",".join([str(weakhash), str(stronghash)]) + "\n"
        read = instream.read(blocksize)


def patchstream(instream, outstream, delta):
    """
    Patches instream using the supplied delta and write the resultantant
    data to outstream.
    """
    blocksize = delta[0]

    for element in delta[1:]:
        if isinstance(element, int) and blocksize:
            instream.seek(element * blocksize)
            element = instream.read(blocksize)
        outstream.write(element)


def rollingchecksum(removed, new, a, b, blocksize=4096):
    """
    Generates a new weak checksum when supplied with the internal state
    of the checksum calculation for the previous window, the removed
    byte, and the added byte.
    """
    a -= removed - new
    b -= removed * blocksize - a
    return (b << 16) | a, a, b


def weakchecksum(data):
    """
    Generates a weak checksum from an iterable set of bytes.
    """
    a = b = 0
    l = len(data)
    for i in range(l):
        a += int(data[i])
        b += (l - i) * int(data[i])

    return (b << 16) | a, a, b
