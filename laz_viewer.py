import sys
import numpy as np
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QPushButton, QFileDialog, QLabel, QSlider, QHBoxLayout)
from PySide6.QtCore import Qt
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtGui import QSurfaceFormat
from OpenGL.GL import *
from OpenGL.GLU import gluPerspective
import laspy


class PointCloudWidget(QOpenGLWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.points = None
        self.colors = None
        self.rotation_x = 0
        self.rotation_y = 0
        self.zoom = -50
        self.last_pos = None
        self.point_size = 2.0
        
    def set_point_cloud(self, points, colors=None):
        """Load point cloud data"""
        self.points = points
        self.colors = colors
        
        # Center the point cloud
        if self.points is not None:
            center = np.mean(self.points, axis=0)
            self.points = self.points - center
            
            # Normalize to fit in view
            max_extent = np.max(np.abs(self.points))
            self.points = self.points / max_extent * 10
            
        self.update()
    
    def initializeGL(self):
        """Initialize OpenGL settings"""
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_POINT_SMOOTH)
        glClearColor(0.1, 0.1, 0.15, 1.0)
        
    def resizeGL(self, w, h):
        """Handle window resize"""
        glViewport(0, 0, w, h)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45, w / h if h != 0 else 1, 0.1, 500.0)
        glMatrixMode(GL_MODELVIEW)
        
    def paintGL(self):
        """Render the point cloud"""
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        
        # Camera position
        glTranslatef(0, 0, self.zoom)
        glRotatef(self.rotation_x, 1, 0, 0)
        glRotatef(self.rotation_y, 0, 1, 0)
        
        if self.points is not None:
            glPointSize(self.point_size)
            glBegin(GL_POINTS)
            
            for i, point in enumerate(self.points):
                if self.colors is not None:
                    glColor3f(*self.colors[i])
                else:
                    # Default color gradient based on height
                    height_normalized = (point[2] - self.points[:, 2].min()) / (
                        self.points[:, 2].max() - self.points[:, 2].min() + 0.001)
                    glColor3f(height_normalized, 0.5, 1.0 - height_normalized)
                
                glVertex3f(*point)
            
            glEnd()
    
    def mousePressEvent(self, event):
        """Store mouse position on click"""
        self.last_pos = event.position()
        
    def mouseMoveEvent(self, event):
        """Handle mouse drag for rotation"""
        if self.last_pos is not None:
            dx = event.position().x() - self.last_pos.x()
            dy = event.position().y() - self.last_pos.y()
            
            if event.buttons() & Qt.LeftButton:
                self.rotation_x += dy
                self.rotation_y += dx
                self.update()
                
            self.last_pos = event.position()
    
    def wheelEvent(self, event):
        """Handle mouse wheel for zoom"""
        delta = event.angleDelta().y()
        self.zoom += delta / 120.0 * 2
        self.zoom = max(-200, min(-5, self.zoom))
        self.update()
    
    def set_point_size(self, size):
        """Change point size"""
        self.point_size = size
        self.update()


class LAZViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LAZ Point Cloud Viewer")
        self.setGeometry(100, 100, 1200, 800)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Info label
        self.info_label = QLabel("No file loaded. Click 'Open LAZ File' to begin.")
        layout.addWidget(self.info_label)
        
        # OpenGL widget for point cloud
        self.gl_widget = PointCloudWidget()
        layout.addWidget(self.gl_widget, stretch=1)
        
        # Controls
        controls_layout = QHBoxLayout()
        
        # Open file button
        open_button = QPushButton("Open LAZ File")
        open_button.clicked.connect(self.open_file)
        controls_layout.addWidget(open_button)
        
        # Point size control
        controls_layout.addWidget(QLabel("Point Size:"))
        self.size_slider = QSlider(Qt.Horizontal)
        self.size_slider.setMinimum(1)
        self.size_slider.setMaximum(10)
        self.size_slider.setValue(2)
        self.size_slider.valueChanged.connect(self.change_point_size)
        controls_layout.addWidget(self.size_slider)
        
        controls_layout.addStretch()
        layout.addLayout(controls_layout)
        
        # Instructions
        instructions = QLabel(
            "Controls: Left-click and drag to rotate | Mouse wheel to zoom | Slider to change point size"
        )
        instructions.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(instructions)
        
    def open_file(self):
        """Open and load a LAZ file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open LAZ File",
            "",
            "LAZ Files (*.laz);;LAS Files (*.las);;All Files (*)"
        )
        
        if file_path:
            try:
                # Read LAZ file
                las = laspy.read(file_path)
                
                # Extract coordinates
                points = np.vstack((las.x, las.y, las.z)).T
                
                # Try to extract colors if available
                colors = None
                if hasattr(las, 'red') and hasattr(las, 'green') and hasattr(las, 'blue'):
                    colors = np.vstack((
                        las.red / 65535.0,
                        las.green / 65535.0,
                        las.blue / 65535.0
                    )).T
                
                # Downsample if too many points (for performance)
                max_points = 50000
                if len(points) > max_points:
                    indices = np.random.choice(len(points), max_points, replace=False)
                    points = points[indices]
                    if colors is not None:
                        colors = colors[indices]
                    self.info_label.setText(
                        f"Loaded {len(points):,} points (downsampled from {len(las.points):,}) from: {file_path}"
                    )
                else:
                    self.info_label.setText(
                        f"Loaded {len(points):,} points from: {file_path}"
                    )
                
                # Load into viewer
                self.gl_widget.set_point_cloud(points, colors)
                
            except Exception as e:
                self.info_label.setText(f"Error loading file: {str(e)}")
    
    def change_point_size(self, value):
        """Update point size"""
        self.gl_widget.set_point_size(value)


def main():
    app = QApplication(sys.argv)
    
    # Set OpenGL format
    fmt = QSurfaceFormat()
    fmt.setDepthBufferSize(24)
    QSurfaceFormat.setDefaultFormat(fmt)
    
    viewer = LAZViewer()
    viewer.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()