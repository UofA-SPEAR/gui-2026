from setuptools import find_packages, setup, Extension
import os
from glob import glob

package_name = 'spear_gui'

egl_bridge = Extension(
    'spear_gui.egl_bridge',
    sources=['spear_gui/egl_bridge.c'],
    include_dirs=[
        '/usr/include/gstreamer-1.0',
        '/usr/include/glib-2.0',
        '/usr/lib/x86_64-linux-gnu/glib-2.0/include',
        '/usr/lib/x86_64-linux-gnu/gstreamer-1.0/include',
    ],
    libraries=['EGL', 'gstgl-1.0', 'gstreamer-1.0', 'gobject-2.0', 'glib-2.0'],
    library_dirs=['/usr/lib/x86_64-linux-gnu'],
)

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('lib/' + package_name, ['spear_gui/Oxanium-Regular.ttf', 'spear_gui/Oxanium-SemiBold.ttf']),
        (os.path.join('share', package_name, 'launch'), glob(os.path.join('launch', '*.py'))),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='root',
    maintainer_email='root@todo.todo',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': ['pytest'],
    },
    entry_points={
        'console_scripts': [
            'main_gui = spear_gui.main_gui:main',
            'camera_node = spear_gui.camera_node:main',
            'rover_camera_manager = spear_gui.rover_camera_manager:main',
        ],
    },
    ext_modules=[egl_bridge],
)