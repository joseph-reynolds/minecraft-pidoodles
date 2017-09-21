# minecraft-pidoodles
Experiments with the original Raspberry Pi Python API mcpi.minecraft

This is not polished code.
This repository contains my notes while I was playing around with the
Raspberry Pi Minecraft APIs.

Setup:
- I used a Raspberry Pi 3 model B loaded with Raspbian Linux,
  which has the special Raspberry Pi version Minecraft pre-loaded.
    $ uname -a
    Linux raspberrypi 4.4.34-v7+ #930 SMP Wed Nov 23 15:20:41 GMT 2016 armv7l GNU/Linux
- I am using the original version of the APIs.  (import mcpi.minecraft)
- I am using Python 2.7.9.  (Sorry for being sloppy with the print statements.)

Accomplishments:
You will find somewere in the code, functions to:
 - build a house, given 2 foundation walls and a height
 - read 2400 minecraft blocks per second (using 200 threads)
 - determine the (x,z) dimensions of the world
 - code to leap/jump 20 blocks up (which stutters as it fights gravity)
 
Ideas:
 - determine the size of the world (x..x, y..y, z..z)
 - given a house foundation, build the entire house
 - clear a large area of blocks
 - dig a shaft or steps down
 - jump to the top of a nearby tree
 - create a miniature world: reduce (256,256) to (16,16)
 - determine ground level (not Minecraft.getHeight)
 - copy/paste a structure
