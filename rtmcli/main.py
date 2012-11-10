# -*- coding: utf-8 -*-
from datetime import datetime
from datetime import timedelta
from docopt import docopt
from rtm.rtm import RTM
import webbrowser
import calendar
import couleur
import pickle
import sys
import os

options = ['%priority',  '@list', '^due',  ':estimate', '#tags']

__doc__ = '''
Usage: rtm show [-a] [<sort>] [<filter>...]
       rtm (add | edit) [%s] <task>...
       rtm (del | done) <task>...
       rtm [list | www | -h]

Options:

-a, --all   Show all task incuding completed
-h, --help  Show this help

''' % ' | '.join(options)

DAYS = {}
for k in ('MONDAY', 'TUESDAY', 'WEDNESDAY',
          'FRIDAY', 'THURSDAY', 'SATURDAY', 'SUNDAY'):
    DAYS[k] = getattr(calendar, k)


class DB(object):
    """Simplistic key/value database"""

    db = os.path.expanduser('~/.rtm.db')

    def __init__(self):
        self.data = {'sort_order': 'dp'}
        if os.path.isfile(self.db):
            with open(self.db, 'rb') as fd:
                self.data = pickle.load(fd)

    def __getattr__(self, attr):
        if attr == 'timeline' and 'timeline' not in self.data:
            timeline = api.timelines.create().timeline
            self.__setattr__(self, 'timeline', timeline)
            return timeline
        return self.data.get(attr)

    def __setattr__(self, attr, value):
        if attr.startswith('_') or attr in ('data', 'db'):
            return object.__setattr__(self, attr, value)
        self.data[attr] = value
        with open(self.db, 'wb') as fd:
            pickle.dump(self.data.copy(), fd)

db = DB()

token = db.token
api = RTM(
        '30919a58f889b783cbb35fe074097d98',
        'cebcd5acab26378c', token)

if token is None:
    print('Give me access here: {0}'.format(api.getAuthURL()))
    raw_input('Press enter once you gave access')
    token = api.getToken()
    db.token = token


class Node(object):
    """Base class for all objects"""

    def __init__(self, node, parent=None, **kwargs):
        self.node = node
        self.parent = parent
        for k, v in kwargs.items():
            setattr(self, k, v)

    @classmethod
    def header(cls):
        keys = cls.keys
        args = [couleur.modifiers.inverse] + keys + [couleur.modifiers.reset]
        return cls.format(*args)

    def __getattr__(self, attr):
        try:
            return getattr(self.node, attr)
        except AttributeError:
            return getattr(self.parent, attr, None)

    def __str__(self):
        return self.format(*[getattr(self, k) for k in self.keys])


class List(Node):
    """A RTM List which get values from DB or api if not yet cached"""

    _lists = {}

    format = '{}'.format
    keys = ['name']

    @classmethod
    def get(cls, id_or_name):
        if not cls._lists:
            cls.values()
        res = cls._lists.get(id_or_name.lower())
        if not res:
            for l in cls.values():
                if l.name.lower().startswith(id_or_name.lower()):
                    return l
        return res

    @classmethod
    def values(cls):
        if not cls._lists:
            dump = db.lists or []
            if not dump:
                for l in api.lists.getList().lists.list:
                    l = cls(l)
                    dump.append(dict(id=l.id, name=l.name))
                db.lists = dump
            for kw in dump:
                l = cls(object(), **kw)
                cls._lists[l.id] = l
                cls._lists[l.name.lower()] = l
        return sorted(cls._lists.values())

    def __cmp__(self, other):
        return cmp(self.name, other.name)


class Task(Node):
    """A printable RTM Task"""

    format = u'{}{:<2} {:<10} {:^10} {:>5} {:<30} {:^13}{}'.format
    keys = ['%P', '@List', '^Due', ':Est.', 'Task', '#tags']
    _tasks = []
    cmps = dict(
            p='priority',
            l='list',
            d='due',
            n='name',
            t='tags',
            e='estimate',
         )

    def __cmp__(self, other):
        _cmp = [self.cmps[a] for a in db.sort_order]
        return cmp(
                [getattr(self, a) or '9999' for a in _cmp],
                [getattr(other, a) or '9999' for a in _cmp])

    @property
    def list(self):
        return self.parent.parent.name

    @property
    def color(self):
        style = self.priority
        if not style:
            style = 'reset'
        if style == '1':
            style = 'red'
        elif style == '2':
            style = 'magenta'
        elif style == '3':
            style = 'yellow'
        elif style == 'N':
            style = 'green'
        value = '%s %s' % (getattr(couleur.forecolors, style),
                                 couleur.modifiers.reset)
        value = couleur.modifiers.inverse + value
        return value

    @property
    def tags(self):
        tags_ = self.__getattr__('tags')
        tags = []
        if tags_:
            tag = tags_.tag
            if isinstance(tag, list):
                tags.extend(tag)
            else:
                tags.append(tag)
        return sorted(['#' + t for t in tags])

    def __str__(self):
        estimate = self.task.estimate
        if estimate:
            estimate, unit = estimate.split(' ')
            estimate = estimate + (unit.startswith('m') and 'mn' or 'h')
        return self.format(couleur.modifiers.reset,
                           self.color,
                           '@' + self.parent.parent.name,
                           self.task.due.split('T')[0],
                           estimate, self.name,
                           ' '.join(self.tags),
                           couleur.modifiers.reset)

    def __repr__(self):
        return '<Task %s>' % self.name

    @classmethod
    def values(cls, **kw):
        if not cls._tasks:
            try:
                lists = api.tasks.getList(**kw).tasks.list
            except AttributeError:
                return []
            for l in lists:
                tasks = getattr(l, 'taskseries', None)
                if tasks:
                    if not isinstance(tasks, list):
                        tasks = [tasks]
                    cls._tasks.extend(
                        [Task(t.task, Node(t, List.get(l.id))) for t in tasks])
        return cls._tasks


def extract_option(prefix, args, unique=True):
    """Extract options like ``@list`` from command line"""
    value = [a for a in args if a.startswith(prefix)]
    if len(value) == 1:
        value = value[0]
        args.remove(value)
        return value[1:]
    elif len(value) > 1 and unique:
        print('More than one %s found in args' % prefix)
        sys.exit(1)
    elif len(value) > 1 and not unique:
        return [v[1:] for v in value]
    return None


def main():
    args = docopt(__doc__, help=False)

    kw = {}
    task = None
    argv = args['<task>'] or []
    argv.append(args['<sort>'] or '')
    argv.extend(args['<filter>'] or [])
    argv = [a for a in argv if a]

    # extract_option
    priority = extract_option('%', argv)
    due = extract_option('^', argv)
    list_name = extract_option('@', argv)
    estimate = extract_option(':', argv)
    tags = extract_option('#', argv)
    if tags and not isinstance(tags, list):
        tags = [tags]

    # determine action
    action = None
    for k in ('add', 'edit', 'del', 'done'):
        if args[k]:
            action = k

    if args['--help']:
        # print help and exit
        print(__doc__.strip())
        sys.exit(0)
    elif args.get('www'):
        # open a browser and exit
        webbrowser.open('https://www.rememberthemilk.com/')
        sys.exit(0)
    elif args.get('lists'):
        # list lists and exit
        for l in List.values():
            print(l)
        sys.exit(0)
    elif argv and args['add']:
        # add a new task
        name = ' '.join(argv)
        if list_name:
            kw['list_id'] = List.get(list_name).id
        kw['timeline'] = db.timeline
        print('Adding task "%s"...' % name)
        res = api.tasks.add(name=name, **kw)
        task = Task(res.list.taskseries.task,
                    Node(res.list.taskseries, List(res.list)))
    elif argv and action in ('edit', 'del', 'done'):
        # find a task befor performing action
        name = ' '.join(argv)
        tasks = Task.values()
        tasks = [t for t in tasks if t.name.lower().startswith(name.lower())]
        if len(tasks) == 1:
            task = tasks[0]
            kw['timeline'] = db.timeline

    if task:
        kw['list_id'] = task.parent.parent.id
        kw['taskseries_id'] = task.parent.id
        kw['task_id'] = task.id
    else:
        # show
        kw = {}
        if args['<filter>'] or args['<sort>'] and argv:
            db.sort_order = argv[0]
        filters = []
        if tags and len(tags) == 1:
            filters.append('tag:"%s"' % tags[0])
        if list_name:
            l = List.get(list_name)
            filters.append('list:"%s"' % l.name)
        if not args['--all']:
            filters.append('status:incomplete')
        if filters:
            kw['filter'] = ' AND '.join(filters)
        print('{}{:^64} {:>10}{}'.format(
                                couleur.modifiers.inverse,
                                datetime.now().strftime('%c'),
                                '(%s)' % db.sort_order,
                                couleur.modifiers.reset))
        print(Task.header())
        for t in sorted(Task.values(**kw)):
            print(t)
        print('')
        if action:
            name = ' '.join(argv)
            print('Task "%s" not found' % name)
            print('')
        sys.exit(0)

    if task and args['del']:
        print('Deleting "%s"...' % task.name)
        api.tasks.delete(**kw)
        sys.exit(0)
    elif task and args['done']:
        print('Completing "%s"...' % task.name)
        print api.tasks.complete(**kw)
        sys.exit(0)
    elif task and args['edit']:
        print('Editing "%s"...' % task.name)

    # take care of options

    if kw and estimate:
        if estimate.endswith('m'):
            unit = 'minutes'
        elif estimate.endswith('h'):
            unit = 'hours'
        elif estimate.endswith('s'):
            unit = 'days'
        estimate = '%s %s' % (estimate[:-1], unit)
        print('Setting estimate to %s' % estimate)
        api.tasks.setEstimate(estimate=estimate, **kw)

    if kw and priority:
        print('Setting priority to %s' % priority)
        api.tasks.setPriority(priority=priority, **kw)

    if kw and tags:
        print('Setting tags to %s' % ', '.join(tags))
        api.tasks.addTags(tags=','.join(tags), **kw)

    if kw and due:
        for k in DAYS:
            if k.lower().startswith(due.lower()):
                due = k
                break
        if due.upper() in DAYS:
            due = DAYS[due.upper()]
            now = datetime.now()
            for i in range(7):
                if calendar.weekday(now.year, now.month, now.day) == due:
                    due = now
                    break
                now += timedelta(1)
        elif due == 'today':
            due = datetime.now()
        elif due.startswith('+'):
            due = datetime.now() + timedelta(int(due[1:]))
        if isinstance(due, datetime):
            print('Setting due date to %s' % due.strftime('%Y-%m-%d'))
            api.tasks.setDueDate(due=due.isoformat().split('.')[0] + 'Z', **kw)

    if task and list_name and args['edit']:
        kw['from_list_id'] = kw.pop('list_id')
        l = List.get(list_name)
        print('Moving to %s' % l.name)
        api.tasks.moveTo(to_list_id=l.id, **kw)
