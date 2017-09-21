#!/usr/bin/python

"""Ideas for minecraft

Ideas:
 - determine the size of the world (x..x, y..y, z..z)
 - given a house foundation, build the entire house
 - clear a large area of blocks
 - dig a shaft or steps down
 - jump to the top of a nearby tree
 - create a miniature world: reduce (256,256) to (16,16)
 - determine ground level (not Minecraft.getHeight)
 - copy/paste a structure

First, we need a faster way to read block data.

Idea to trigger building a house:
 - hit a wall near a torch on top of a gold block

Function to build an entire house (a hollow box) given its dimensions.
To use this function,
start with a flat field
build two low walls that meet at a right angle
to indicate the area of your house,
and a post (a stack of blocks) on the corner to indicate the height.
Place a torch at ground level exactly at the inside corner of your house.
Stand on or immediately next to the torch.
Then run this function ("Algorithm to build a house" below).
--> The function locates the nearby torch, and the corner of your house.
    Then it scans the foundation to learn how big to make it.
    Finally, it puts the walls up.

It doesn't matter what direction the corner is facing, as long as
there is a torch on the insde corner.  For example, if "x" is a block
and " "(space) is air, "t" is a torch, and "X"(capital x) is a stack of
blocks, the following top-view shows the required layout:

  Xxxxxxxx                 x
  xt                       x
  x              or        x
  x                       tx
  x                    xxxxX

Idea: memoize results from mc.getBlock
"""

# mcpi is found in /usr/lib/python2.7/dist-packages

import mcpi.minecraft as minecraft
import mcpi.block as block
from   mcpi.vec3 import Vec3
from   mcpi.connection import Connection
import time
import timeit
import Queue
import threading

def vec3_get_sign(self):
    # Warning: hack! Assumes unit vector
    return self.x + self.y + self.z
Vec3.get_sign = vec3_get_sign

class TorchFindError(Exception):
    """Torch not found nearby"""
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class CornerFindError(Exception):
    """Corner not found"""
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

def different_block(b):
    if   b == block.STONE.id:      b = block.SANDSTONE.id
    elif b == block.SANDSTONE.id:  b = block.DIRT.id
    elif b == block.DIRT.id:       b = block.WOOD.id
    else:                          b = block.STONE.id
    return b


def get_nearby_torchpos(p):
    """Return the position of a nearby torch"""
    torchpos = None
    search_size = 1
    for x in range(int(p.x - search_size), int(p.x + search_size+1)):
        for z in range(int(p.z - search_size), int(p.z + search_size+1)):
            b = mc.getBlock(x, p.y, z)
            if b == block.TORCH.id:
                if not torchpos is None:
                    raise TorchFindError("Too many torches")
                torchpos = Vec3(x, p.y, z)
    if torchpos is None:
        raise TorchFindError("Torch not found nearby")
    return torchpos

def get_corner_data(pos):
    """Returns data about a corner next to the input position.

    A "corner" is two walls meeting at right angles with a post.
    The walls and post define the corner.
    The input position should be the inside corner at ground level
    such as returned by get_nearby_torchpos.
    The return value is a 2-tuple:
     - The corner position
     - A unit vector pointing "inside" the corner
    """
    # Read blocks around the input pos
    blocks = []  # Usage: blocks[x][z]
    mask = 0     # Bit mask: abcdefghi, like:
                 #   adg
                 #   beh
                 #   cfi
    for x in range(int(pos.x - 1), int(pos.x + 2)):
        col = []
        for z in range(int(pos.z - 1), int(pos.z + 2)):
            b = mc.getBlockWithData(x, pos.y, z)  # Test
            b = mc.getBlock(x, pos.y, z)
            col.append(b)
            mask = (mask << 1) + (0 if b == block.AIR.id else 1)
        blocks.append(col)
    mask &= 0b111101111  # Mask off center block
    # print "Mask", format(mask,"#011b")
    nw_corner_mask = 0b111100100
    ne_corner_mask = 0b100100111
    sw_corner_mask = 0b111001001
    se_corner_mask = 0b001001111
    if mask == nw_corner_mask:
        corner = Vec3(pos.x - 1, pos.y, pos.z - 1)
        vector = Vec3(1, 1, 1)
    elif mask == ne_corner_mask:
        corner = Vec3(pos.x +1, pos.y, pos.z - 1)
        vector = Vec3(-1, 1, 1)
    elif mask == sw_corner_mask:
        corner = Vec3(pos.x - 1, pos.y, pos.z + 1)
        vector = Vec3(1, 1, -1)
    elif mask == se_corner_mask:
        corner = Vec3(pos.x + 1, pos.y, pos.z + 1)
        vector = Vec3(-1, 1, -1)
    else:
        raise CornerFindError("Corner not found")
    return corner, vector

def get_length_of_block_run(startpos, vector):
    """determine the length of a run of blocks

    parameters: startpos is the starting block
    vector is a unit vector in the direction to count
    """
    ans = 0
    pos = startpos
    while mc.getBlock(pos) != block.AIR.id:
        ans += 1
        pos = pos + vector
    ans -= 1
    return ans * vector.get_sign()

def get_house_data(pos):
    corner, vector = get_corner_data(pos)
    sizex = get_length_of_block_run(corner, Vec3(vector.x, 0, 0))
    sizey = get_length_of_block_run(corner, Vec3(0, vector.y, 0))
    sizez = get_length_of_block_run(corner, Vec3(0, 0, vector.z))
    return corner, Vec3(sizex, sizey, sizez)

def do_house(corner, dim):
    newblockid = different_block(mc.getBlock(corner))
    # Unit test: just do a chimney
    #mc.setBlocks(corner.x, corner.y, corner.z,
    #             corner.x, corner.y + dim.y, corner.z,
    #             newblockid)
    # Near wall along x direction
    mc.setBlocks(corner.x,         corner.y,         corner.z,
                 corner.x + dim.x, corner.y + dim.y, corner.z,
                 newblockid)
    # Near wall along z direction
    mc.setBlocks(corner.x, corner.y,         corner.z,
                 corner.x, corner.y + dim.y, corner.z + dim.z,
                 newblockid)


mc = minecraft.Minecraft.create()

#p = mc.player.getTilePos()
#mc.x_connect_multiple(p.x, p.y+2, p.z, block.GLASS.id)
#print 'bye!'
#exit(0)

# Algorithm to build a house
for i in range(0,0):
    time.sleep(1)
    p = mc.player.getTilePos()
    b = mc.getBlock(p.x, p.y-1, p.z)
    info = ""
    try:
        tp = get_nearby_torchpos(p)
        info = "torch found"
        try:
            c,v = get_house_data(tp)
            info = "corner found"
            do_house(c,v)
        except CornerFindError as e:
            pass
    except TorchFindError as e:
        pass # print "TorchFindError:", e.value
    print b, info

connections = []
def get_blocks_in_parallel(c1, c2, degree=35):
    """get a cuboid of block data

    parms:
        c1, c2: the corners of the cuboid
        degree: the degree of parallelism (number of sockets)
    returns:
        map from mcpi.vec3.Vec3 to mcpi.block.Block
    """
    # Set up the work queue
    c1.x, c2.x = sorted((c1.x, c2.x))
    c1.y, c2.y = sorted((c1.y, c2.y))
    c1.z, c2.z = sorted((c1.z, c2.z))
    workq = Queue.Queue()
    for x in range(c1.x, c2.x+1):
        for y in range(c1.y, c2.y+1):
            for z in range(c1.z, c2.z+1):
                workq.put((x,y,z))
    print "Getting data for %d blocks" % workq.qsize()

    # Create socket connections, if needed
    # TO DO: Bad! Assumes degree is a constant
    # To do: close the socket
    global connections
    if not connections:
        connections = [Connection("localhost", 4711) for i in range(0,degree)]

    # Create worker threads
    def worker_fn(connection, workq, outq):
        try:
          while True:
            pos = workq.get(False)
            # print "working", pos[0], pos[1], pos[2]
            connection.send("world.getBlockWithData", pos[0], pos[1], pos[2])
            ans = connection.receive()
            blockid, blockdata = map(int, ans.split(","))
            outq.put((pos, (blockid, blockdata)))
        except Queue.Empty:
            pass
    outq = Queue.Queue()
    workers = []
    for w in range(degree):
        t = threading.Thread(target = worker_fn,
                             args = (connections[w], workq, outq))
        t.start()
        workers.append(t)

    # Wait for workers to finish
    for w in workers:
        # print "waiting for", w.name
        w.join()

    # Collect results
    answer = {}
    while not outq.empty():
        pos, block = outq.get()
        answer[pos] = block
    return answer


while False:
    # mc.getHeight works
    ppos = mc.player.getPos()
    h = mc.getHeight(ppos.x, ppos.z)
    print h
    time.sleep(1)

if False:
    """
    degree = 200
    corner1 = Vec3(-50, 8, -50)
    corner2 = Vec3( 50, 8,  50)
    starttime = timeit.default_timer()
    blks = get_blocks_in_parallel(corner1, corner2, degree)
    endtime = timeit.default_timer()
    print endtime-starttime, 'get_blocks_in_parallel'
    blks = get_blocks_in_parallel(corner1, corner2, degree)
    endtime2 = timeit.default_timer()
    print endtime2-endtime, 'get_blocks_in_parallel again'

    for z in range(corner1.z, corner2.z):
        s = ""
        for x in range(corner1.x, corner2.x):
            c = " " if blks[(x, 8, z)][0] == block.AIR.id else "x"
            s = s + c
        print s
    """

    # Performance experiments
    """Results:
        Hardware: Raspbery Pi 3 Model B V1.2 with heat sink
        Linux commands show:
          $ uname -a
          Linux raspberrypi 4.4.34-v7+ #930 SMP Wed Nov 23 15:20:41 GMT 2016 armv7l GNU/Linux
          $ lscpu
          Architecture:          armv7l
          Byte Order:            Little Endian
          CPU(s):                4
          On-line CPU(s) list:   0-3
          Thread(s) per core:    1
          Core(s) per socket:    4
          Socket(s):             1
          Model name:            ARMv7 Processor rev 4 (v7l)
          CPU max MHz:           1200.0000
          CPU min MHz:           600.0000
        GPU memory is 128 (unit is Mb, I think)

        Test getting 10201 blocks, and stack_size=128Kb
        varying the number of threads:
           threads   time(sec)  blocks/sec
           -------   ---------  ----------
            10       39.87
            25       19.46
            50       10.68
            75        7.29
           100        5.57
           115        5.01
           120        4.86
           125        4.75
           130        4.58
           150        4.47
           175        4.55
           200        4.24
           250        4.41
           400        4.60
        Observations:
         - Each thread process 15 to 25 blocks/sec
         - Some blocks take much longer to fetch, about 0.3 sec
         - performance peaks with 200 threads, at 2400 blocks/sec
         - creating threads is not free
            - can create 50 threads in 1 sec, 100 threads in 2.5 sec
            - memory consumption increases (not measured)
         - the tests were repeated while the game was being
           played interactively, specifically, flying at altitude
           and looking down so that new blocks were being fetched
           as quickly as possible.  This did not affect performance:
            + no graphical slowdowns or glitches were observed
            + the performance of fetching blocks was not affected
        Note:
            The expected case is to create the required threads once
            and keep them around for the lifetime of the program.
            The experimental code was designed to do just that.
            Some data was captured that suggests how expensive
            starting up hundreds of threads is.  Although it was
            not one of the objectives of the original study, it is
            given as an interesting observation.
        Conclusions:
           Eyeballing the data suggests that 200 threads is optimal.
           However, if the 6 seconds it takes to create the threads
           is not acceptable, consider using 100 threads which is
           about 30% slower, but only takes 1 second to create the
           threads.
    """
    threading.stack_size(128*1024)
    for degree in [100, 150, 200]:
        connections = []
        corner1 = Vec3(-50, 8, -50)
        corner2 = Vec3( 50, 8,  50)
        starttime = timeit.default_timer()
        blks = get_blocks_in_parallel(corner1, corner2, degree)
        endtime = timeit.default_timer()
        blks = get_blocks_in_parallel(corner1, corner2, degree)
        endtime2 = timeit.default_timer()
        print "entries=10201 degree=%s time1=%s time2=%s" % (
            str(degree),
            str(endtime-starttime),
            str(endtime2-endtime))


# Idea: class for get_blocks_in_parallel()
class ParallelGetter:
    """Get block data from the Mincraft Pi API -- NOT FINISHED"""
    def __init__(self, address = "localhost", port = 4711, parallelism=200):
        self.address = address
        self.port = port
        self.parallelism = parallelism
        self.connections = [Connection(address, port) for i in range(parallelism)]
        # To do: close the socket connection

    @staticmethod
    def normalize_corners(c1, c2):
        """ensure c1.x <= c2.x, etc., without changing the cuboid"""
        c1.x, c2.x = sorted((c1.x, c2.x))
        c1.y, c2.y = sorted((c1.y, c2.y))
        c1.z, c2.z = sorted((c1.z, c2.z))
        return c1, c2

    @staticmethod
    def generate_work_items_xyz(c1, c2):
        c1, c2 = normalize_corners(c1, c2)
        workq = Queue.Queue()
        for x in range(c1.x, c2.x+1):
            for y in range(c1.y, c2.y+1):
                for z in range(c1.z, c2.z+1):
                    workq.put((x,y,z))
        return workq

    @staticmethod
    def _unpack_int(self, response):
        return int(response)

    @staticmethod
    def _unpack_int_int(self, response):
        i1, i2 = map(int, response.split(","))
        return i1, i2

    def get_blocks(self, c1, c2):
        workq = generate_work_items_xyz(c, c2)
        return _do_work(workq, "world.getBlock", _unpack_int)

    def get_blocks_with_data(self, c1, c2):
        workq = generate_work_items_xyz(c, c2)
        return _do_work(workq, "world.getBlockWithData", _unpack_int_int)

    def _do_work(self, workq, api_name, unpack_fn):
        """Perform the parallel portion of the work.

        parms:
            workq - such as from generate_work_items_xyz

        Specifically, start a worker thread for each connection,
        Each worker feeds work from the workq to the API, formats
        the results, and enqueues the results.
        When there is no more work, the workers quit, and the
        return value is computed.
        """
        def worker_fn(connection, workq, outq, unpack_fn):
            try:
              while True:
                pos = workq.get(False)
                connection.send(api_name, pos)
                outq.put((pos, unpack_fn(connection.receive())))
            except Queue.Empty:
                pass
        # Create worker threads
        outq = Queue.Queue()
        workers = []
        for w in range(parallelism):
            t = threading.Thread(
                target = worker_fn,
                args = (connections[w], workq, outq, unpack_fn))
            t.start()
            workers.append(t)
        # Wait for workers to finish, then collect their data
        for w in workers:
            w.join()
        answer = {}
        while not outq.empty():
            pos, data = outq.get()
            answer[pos] = data
        return answer





"""Idea: Tree jumper
You can jump from tree to tree.
If you are
    (a) on a tree (LEAVES = Block(18)),
    (b) moving forward, and
    (c) jumping,
you will jump/fly to the nearest tree in your path.
Algorithm:
    while True:
        player_velocity = "track player position to determine velocity"
        if "player is moving and on a leaf and jumps":
            destination = "find nearest tree(player_pos, player_vel)"
            if destination:
                parabola = compute(player_pos, destination)
                "move player smoothly along the parabola"
                "if player hits a block: break"
where
    def nearest_tree(player_pos, player_vel):
        search_areas = [
            player_pos + 30 * player_vel with radius=15,
            player_pos + 15 * player_vel with radius=10,
            player_pos + 40 * player_vel with radius=15]
        search areas *= [player_pos.y, player_pos.y-7, player_pos+7]
        for area in search_areas:
            fetch a plane of block data centered at (area)
            tree = find tree, prefering center of the area
            if tree: return tree
        return tree
    def compute_parabola():
        gravity = 0.3  # blocks/time**2
        xz_distance = sqrt(xd**2 + zd**2)
        xz_speed = 1
        total_time = xz_distance / xz_speed
        x_vel = xd / total_time
        z_vel = zd / total_time
        y_vel = ((-yd / total_time) +
                 ((0.5 * gravity * (total_time ** 2)))

"""
# Lets' try a leap/jump
if False:
    # mc.player.setPos(1, 4, 3) # if the jump goes badly wrong
    ppos = mc.player.getPos()
    x = ppos.x
    y = ppos.y
    z = ppos.z
    xv = 0.005
    yv = 0.1
    zv = 0.02
    while yv > 0:
        mc.player.setPos(x, y, z)
        x += xv
        y += yv
        z += zv
        yv -= 0.0001
        time.sleep(0.001)

# Try stacking up multiple getBlocks:
if True:
    """This code is weird.  Delete it!"""
    connection = Connection("localhost", 4711)
    for x in range(-20, 20):
        for z in range(-20, 20):
            connection.send("world.getBlockWithData", x, 2, z)

    print connection.receive()
    print connection.receive()

# How big is the world?
if False:
    corner1 = Vec3(-200, 0, 0)
    corner2 = Vec3(200, 0, 0)
    degree = 150
    xaxis = get_blocks_in_parallel(corner1, corner2, degree)
    xmin = xmax = 0
    for x in range(200):
        if xaxis[(x, 0, 0)][0] == block.BEDROCK_INVISIBLE.id:
            xmax = x - 1
            break
    for x in range(0, -200, -1):
        if xaxis[(x, 0, 0)][0] == block.BEDROCK_INVISIBLE.id:
            xmin = x + 1
            break
    #print "X-axis: %d to %d" % (xmin, xmax)

    corner1 = Vec3(0, 0, 200)
    corner2 = Vec3(0, 0, -200)
    degree = 150
    zaxis = get_blocks_in_parallel(corner1, corner2, degree)
    zmin = zmax = 0
    for z in range(200):
        if zaxis[(0, 0, z)][0] == block.BEDROCK_INVISIBLE.id:
            zmax = z - 1
            break
    for z in range(0, -200, -1):
        if zaxis[(0, 0, z)][0] == block.BEDROCK_INVISIBLE.id:
            zmin = z + 1
            break
    #print "Z-axis: %d to %d" % (zmin, zmax)

    print "The world is: [%d..%d][y][%d..%d]" % (
        xmin, xmax, zmin, zmax)

###
### Try stuff with sockets
###
'''
I have not finished coding this part.
def gen_answers(connection, requests, format, parse_fn):
    """generate answers for each request, like (req, answer)"""
    request_buf = io.BufferedWriter(connection.socket.makefile('w'))
    response_buf = io.BufferedReader(connection.socket.makefile('r'))
    request_queue = []
    while True:
        # Write requests into request_buffer
        #   ...to do...
        # Perform socket I/O
        Communicate:
            r,w,e = select.select([response_buf], [request_buf], [], 1)
            if r:
                response_data = response_buf.peek()
                if "response_data has a newline at position n":
                    response_text = response_buf.read(n)

                response_buf.read(???)
            if w:
                request_buf.write(???)
        # Read answers
        while resp_buf.hasSomeData:
            request = request_queue[0]  # Er, use a queue?
            request_queue = request_queue[1:]
            response = parse_fn(response_buf.readline())
            yield (request, response)

Hmmm, my sockets are rusty, and my Python io buffer classes weak,
  but this seems more correct:
    # We write requests (like b"world.getBlock(0,0,0)" into the
    # request_buffer and then into the request_file (socket).
    request_buffer = bytearray()  # bytes, bytearray, or memoryview
    request_file = io.FileIO(connection.socket.fileno(), "w", closeFd=False)
    "...append data to request_buffer..."
    if request_buffer: can select
    if selected:
        # Write exactly once
        bytes_written = request_file.write(request_buffer)
        request_buffer = request_buffer[bytes_written:]
        if bytes_written == 0: "something is wrong"

    # We read responses (like b"2") from the response_file (socket)
    # into the response_buffer.
    response_file = io.FileIO(connection.socket.fileno(), "r", closeFd=False)
    response_buffer = bytes()
    if selected:
        # Read exactly once
        response_buffer.append(response_file.read())
    "...remove data from response_buffer..."


# Try gen_answers:
if True:
    connection = Connection("localhost", 4711)
    def some_rectangle():
        for x in range(-2,2):
            for z in range(-2,2):
                yield (x, 0, z)
    for pos, blk in gen_answers(connection,
                                some_rectangle,
                                "world.getBlock(%d,%d)",
                                int):
        print "Got", pos, blk

    my_blocks = {}
    for pos, blk in gen_answers(connection,
                                some_rectangle,
                                "world.getBlock(%d,%d)",
                                int):
        my_blocks[pos] = blk
'''
