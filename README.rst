=========================================
Remember The Milk command line interface
=========================================

Yeah. I'm trying to get organized. So I wrote this lightweigth CLI for
https://www.rememberthemilk.com/.

If you want a more advanced CLI you can have a look at `rtm
<http://www.davidwaring.net/projects/rtm.html>`_.

It contains much more feature.

Instalation
===========

With pip::

  $ pip install git://github.com/gawel/rtm-cli.git

Usage
=====

Show list @Work::

  $ rtm show @w

Show list @Work sorted by priority::

  $ rtm show p @work

Show list @Work sorted by due date and priority::

  $ rtm show dp @work

Add a Work task estimated to 5mn for tomorrow::

  $ rtm add @Work :5mn ^+1 Make some coffee

Add a task due for next wednesday with high priority::
  $ rtm add %1 ^wednesday Make some coffee

Edit a task. Change due date an list::

  $ rtm edit ^+7 @work Make some coffee

Mark task complete::

  $ rtm done Make some

Delete a task::

  $ rtm del Make some

Sort key
========

Here are the available sort keys:

- p: priority
- l: list name
- d: due date
- n: name
- t: tags
- e: estimate
