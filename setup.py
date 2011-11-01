from setuptools import setup

kwargs = {
    'name': 'django-xcomments',
    'version': '0.1',
    'description': 'Django commenting framework, contrib.comments +threaded +ajax +rating +caching.',
    'author': 'Tartnskyi Vladimir',
    'author_email': 'fon.vosi@gmail.com',
    'url': 'https://github.com/vosi/django-xcomments',
    'keywords': 'django,comments',
    'license': 'BSD',
    'packages': ['comments',],
    'include_package_data': True,
    'install_requires': ['setuptools'],
    'zip_safe': False,
    'classifiers': [
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Utilities',
    ],
}
setup(**kwargs)
