import sys
import os
import numpy as np
from scipy.interpolate import griddata
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                               QPushButton, QFileDialog, QLabel, QSlider, QHBoxLayout,
                               QCheckBox, QLineEdit)
from PySide6.QtCore import Qt
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtGui import QSurfaceFormat, QImage
from OpenGL.GL import *
from OpenGL.GLU import gluPerspective
from OpenGL.arrays import vbo
import laspy


class PointCloudWidget(QOpenGLWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.points = None
        self.colors = None
        self.rotation_x = 0
        self.rotation_y = 0
        self.zoom = -50
        self.pan_x = 0
        self.pan_y = 0
        self.last_pos = None
        self.point_size = 2.0
        self.vbo_vertices = None
        self.vbo_colors = None
        self.num_points = 0

        # Map overlay properties
        self.map_textures = []  # List of (texture_id, x, y, size) tuples
        self.show_overlay = True
        self.overlay_alpha = 0.7
        self.ground_height = -10  # Height of the ground plane
        self.point_cloud_bounds = None  # (min_x, max_x, min_y, max_y, min_z, max_z)

        # Terrain mesh for draping textures
        self.terrain_mesh = None  # Will store (vertices, tex_coords, indices)
        self.terrain_vbo_vertices = None
        self.terrain_vbo_texcoords = None
        self.terrain_indices = None
        
    def set_point_cloud(self, points, colors=None):
        """Load point cloud data"""
        # Store original bounds before centering
        bounds = (
            points[:, 0].min(), points[:, 0].max(),
            points[:, 1].min(), points[:, 1].max(),
            points[:, 2].min(), points[:, 2].max()
        )

        # Center the point cloud
        center = np.mean(points, axis=0)
        points = points - center

        # Normalize to fit in view
        max_extent = np.max(np.abs(points))
        points = points / max_extent * 10

        # Store normalized bounds for ground plane positioning
        self.point_cloud_bounds = (
            points[:, 0].min(), points[:, 0].max(),
            points[:, 1].min(), points[:, 1].max(),
            points[:, 2].min(), points[:, 2].max()
        )
        self.ground_height = self.point_cloud_bounds[4]  # min_z

        # Generate colors if not provided
        if colors is None:
            # Height-based gradient
            z_min, z_max = points[:, 2].min(), points[:, 2].max()
            height_normalized = (points[:, 2] - z_min) / (z_max - z_min + 0.001)
            colors = np.column_stack([
                height_normalized,
                np.full(len(points), 0.5),
                1.0 - height_normalized
            ])

        # Store data
        self.points = points.astype(np.float32)
        self.colors = colors.astype(np.float32)
        self.num_points = len(points)

        # Create VBOs if OpenGL context is ready
        if self.context():
            self.makeCurrent()
            self._create_vbos()
            self.doneCurrent()

        # Generate terrain mesh for texture draping
        self._generate_terrain_mesh()

        self.update()

    def _generate_terrain_mesh(self, grid_resolution=100):
        """Generate a terrain mesh from point cloud by interpolating heights"""
        if self.points is None or self.point_cloud_bounds is None:
            return

        min_x, max_x, min_y, max_y, min_z, max_z = self.point_cloud_bounds

        # Create regular grid
        grid_x = np.linspace(min_x, max_x, grid_resolution)
        grid_y = np.linspace(min_y, max_y, grid_resolution)
        grid_xx, grid_yy = np.meshgrid(grid_x, grid_y)

        # Interpolate Z values from point cloud
        print(f"Generating terrain mesh with {grid_resolution}x{grid_resolution} grid...")
        grid_zz = griddata(
            self.points[:, :2],  # XY points from point cloud
            self.points[:, 2],   # Z values
            (grid_xx, grid_yy),  # Grid points to interpolate to
            method='linear',      # Use linear interpolation
            fill_value=min_z     # Fill areas outside point cloud with min height
        )

        # Create vertices array (flattened)
        vertices = []
        tex_coords = []
        for i in range(grid_resolution):
            for j in range(grid_resolution):
                vertices.append([grid_xx[i, j], grid_yy[i, j], grid_zz[i, j]])
                # Texture coordinates normalized to 0-1
                tex_coords.append([j / (grid_resolution - 1), i / (grid_resolution - 1)])

        vertices = np.array(vertices, dtype=np.float32)
        tex_coords = np.array(tex_coords, dtype=np.float32)

        # Create triangle indices for the mesh
        indices = []
        for i in range(grid_resolution - 1):
            for j in range(grid_resolution - 1):
                # Two triangles per quad
                idx = i * grid_resolution + j
                # Triangle 1
                indices.extend([idx, idx + grid_resolution, idx + 1])
                # Triangle 2
                indices.extend([idx + 1, idx + grid_resolution, idx + grid_resolution + 1])

        self.terrain_indices = np.array(indices, dtype=np.uint32)

        # Store mesh data
        self.terrain_mesh = (vertices, tex_coords)

        # Create VBOs if context is available
        if self.context():
            self.makeCurrent()
            self._create_terrain_vbos()
            self.doneCurrent()

        print(f"Terrain mesh generated: {len(vertices)} vertices, {len(indices)//3} triangles")

    def _create_terrain_vbos(self):
        """Create VBOs for terrain mesh"""
        if self.terrain_mesh is None:
            return

        # Clean up old VBOs
        if self.terrain_vbo_vertices is not None:
            self.terrain_vbo_vertices.delete()
        if self.terrain_vbo_texcoords is not None:
            self.terrain_vbo_texcoords.delete()

        vertices, tex_coords = self.terrain_mesh
        self.terrain_vbo_vertices = vbo.VBO(vertices)
        self.terrain_vbo_texcoords = vbo.VBO(tex_coords)

    def _create_vbos(self):
        """Create Vertex Buffer Objects for efficient rendering"""
        if self.vbo_vertices is not None:
            self.vbo_vertices.delete()
        if self.vbo_colors is not None:
            self.vbo_colors.delete()

        self.vbo_vertices = vbo.VBO(self.points)
        self.vbo_colors = vbo.VBO(self.colors)

    def load_map_tiles(self, tiles_path, zoom_level=15):
        """Load map tiles from directory structure and create texture atlas"""
        self.clear_map_textures()

        zoom_path = os.path.join(tiles_path, str(zoom_level))

        if not os.path.exists(zoom_path):
            print(f"Zoom level {zoom_level} not found at {zoom_path}")
            return

        # Get all x directories
        x_dirs = sorted([d for d in os.listdir(zoom_path)
                        if os.path.isdir(os.path.join(zoom_path, d))], key=int)

        if not x_dirs:
            print(f"No tiles found for zoom level {zoom_level}")
            return

        # First pass: collect all tiles and determine grid size
        tile_data = {}  # (x, y) -> QImage
        min_tile_x = min_tile_y = float('inf')
        max_tile_x = max_tile_y = float('-inf')

        for x_dir in x_dirs:
            x = int(x_dir)
            x_path = os.path.join(zoom_path, x_dir)
            y_files = [f for f in os.listdir(x_path) if f.endswith('.tile')]

            for y_file in y_files:
                y_str = y_file.replace('.tile', '').replace('png', '').replace('jpg', '').replace('jpeg', '')
                try:
                    y = int(y_str)
                except ValueError:
                    continue

                tile_path = os.path.join(x_path, y_file)
                image = QImage(tile_path)
                if not image.isNull():
                    tile_data[(x, y)] = image.convertToFormat(QImage.Format_RGBA8888)
                    min_tile_x = min(min_tile_x, x)
                    max_tile_x = max(max_tile_x, x)
                    min_tile_y = min(min_tile_y, y)
                    max_tile_y = max(max_tile_y, y)

        if not tile_data:
            print("No valid tiles found")
            return

        # Create texture atlas by combining all tiles into one image
        tile_size = 256
        grid_width = int(max_tile_x - min_tile_x + 1)
        grid_height = int(max_tile_y - min_tile_y + 1)
        atlas_width = grid_width * tile_size
        atlas_height = grid_height * tile_size

        print(f"Creating texture atlas: {grid_width}x{grid_height} tiles = {atlas_width}x{atlas_height} pixels")

        # Create combined image
        atlas = QImage(atlas_width, atlas_height, QImage.Format_RGBA8888)
        atlas.fill(0)  # Fill with transparent black

        # Composite all tiles into the atlas
        from PySide6.QtGui import QPainter
        painter = QPainter(atlas)
        for (tx, ty), img in tile_data.items():
            dest_x = (tx - min_tile_x) * tile_size
            dest_y = (ty - min_tile_y) * tile_size
            painter.drawImage(dest_x, dest_y, img)
        painter.end()

        # Need OpenGL context
        if not self.context():
            print("No OpenGL context available")
            return

        self.makeCurrent()

        # Create single OpenGL texture from atlas
        texture_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, texture_id)

        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)

        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, atlas.width(), atlas.height(),
                   0, GL_RGBA, GL_UNSIGNED_BYTE, atlas.bits())

        # Store single texture atlas
        self.map_textures = [(texture_id, 0, 0, 0)]  # Single texture

        print(f"Texture atlas created: {len(tile_data)} tiles combined")
        self.doneCurrent()
        self.update()

    def clear_map_textures(self):
        """Delete all loaded map textures"""
        if self.context() and self.map_textures:
            self.makeCurrent()
            for texture_id, _, _, _ in self.map_textures:
                glDeleteTextures([texture_id])
            self.doneCurrent()
        self.map_textures = []

    def set_overlay_alpha(self, alpha):
        """Set overlay transparency (0.0 = transparent, 1.0 = opaque)"""
        self.overlay_alpha = alpha
        self.update()

    def toggle_overlay(self, show):
        """Toggle map overlay visibility"""
        self.show_overlay = show
        self.update()

    def initializeGL(self):
        """Initialize OpenGL settings"""
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_POINT_SMOOTH)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_TEXTURE_2D)
        glClearColor(0.1, 0.1, 0.15, 1.0)

        # Create VBOs if we have data
        if self.points is not None:
            self._create_vbos()
        
    def resizeGL(self, w, h):
        """Handle window resize"""
        glViewport(0, 0, w, h)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45, w / h if h != 0 else 1, 0.1, 500.0)
        glMatrixMode(GL_MODELVIEW)
        
    def paintGL(self):
        """Render the point cloud and map overlay"""
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()

        # Camera position
        glTranslatef(0, 0, self.zoom)
        glRotatef(self.rotation_x, 1, 0, 0)
        glRotatef(self.rotation_y, 0, 1, 0)
        glTranslatef(self.pan_x, self.pan_y, 0)

        # Render map overlay first (behind points)
        if self.show_overlay and self.map_textures and self.point_cloud_bounds:
            self._render_map_overlay()

        # Render point cloud
        if self.vbo_vertices is not None and self.vbo_colors is not None:
            glDisable(GL_TEXTURE_2D)
            glPointSize(self.point_size)

            # Enable vertex and color arrays
            glEnableClientState(GL_VERTEX_ARRAY)
            glEnableClientState(GL_COLOR_ARRAY)

            # Bind and set vertex data
            self.vbo_vertices.bind()
            glVertexPointer(3, GL_FLOAT, 0, None)

            # Bind and set color data
            self.vbo_colors.bind()
            glColorPointer(3, GL_FLOAT, 0, None)

            # Draw all points at once
            glDrawArrays(GL_POINTS, 0, self.num_points)

            # Cleanup
            self.vbo_vertices.unbind()
            self.vbo_colors.unbind()
            glDisableClientState(GL_VERTEX_ARRAY)
            glDisableClientState(GL_COLOR_ARRAY)

    def _render_map_overlay(self):
        """Render map texture draped over 3D terrain mesh"""
        if not self.map_textures or not self.terrain_vbo_vertices or not self.terrain_vbo_texcoords:
            return

        glEnable(GL_TEXTURE_2D)
        glColor4f(1.0, 1.0, 1.0, self.overlay_alpha)

        # Bind the texture atlas
        texture_id = self.map_textures[0][0]
        glBindTexture(GL_TEXTURE_2D, texture_id)

        # Enable vertex and texture coordinate arrays
        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_TEXTURE_COORD_ARRAY)

        # Bind vertex data
        self.terrain_vbo_vertices.bind()
        glVertexPointer(3, GL_FLOAT, 0, None)

        # Bind texture coordinate data
        self.terrain_vbo_texcoords.bind()
        glTexCoordPointer(2, GL_FLOAT, 0, None)

        # Draw the terrain mesh as triangles
        glDrawElements(GL_TRIANGLES, len(self.terrain_indices), GL_UNSIGNED_INT, self.terrain_indices)

        # Cleanup
        self.terrain_vbo_vertices.unbind()
        self.terrain_vbo_texcoords.unbind()
        glDisableClientState(GL_VERTEX_ARRAY)
        glDisableClientState(GL_TEXTURE_COORD_ARRAY)
        glDisable(GL_TEXTURE_2D)
    
    def mousePressEvent(self, event):
        """Store mouse position on click"""
        self.last_pos = event.position()
        
    def mouseMoveEvent(self, event):
        """Handle mouse drag for rotation and panning"""
        if self.last_pos is not None:
            dx = event.position().x() - self.last_pos.x()
            dy = event.position().y() - self.last_pos.y()

            if event.buttons() & Qt.LeftButton:
                # Left button: rotate
                self.rotation_x += dy
                self.rotation_y += dx
                self.update()
            elif event.buttons() & Qt.RightButton or event.buttons() & Qt.MiddleButton:
                # Right or middle button: pan
                # Scale pan speed based on zoom level
                pan_speed = abs(self.zoom) / 50.0
                self.pan_x += dx * pan_speed * 0.02
                self.pan_y -= dy * pan_speed * 0.02
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
        self.setWindowTitle("LAZ Point Cloud Viewer with Map Overlay")
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

        # Point cloud controls
        pc_controls_layout = QHBoxLayout()

        # Open file button
        open_button = QPushButton("Open LAZ File")
        open_button.clicked.connect(self.open_file)
        pc_controls_layout.addWidget(open_button)

        # Point size control
        pc_controls_layout.addWidget(QLabel("Point Size:"))
        self.size_slider = QSlider(Qt.Horizontal)
        self.size_slider.setMinimum(1)  # Will represent 0.1
        self.size_slider.setMaximum(100)  # Will represent 10.0
        self.size_slider.setValue(20)  # Default 2.0
        self.size_slider.valueChanged.connect(self.change_point_size)
        pc_controls_layout.addWidget(self.size_slider)

        self.size_label = QLabel("2.0")
        pc_controls_layout.addWidget(self.size_label)

        pc_controls_layout.addStretch()
        layout.addLayout(pc_controls_layout)

        # Map overlay controls
        map_controls_layout = QHBoxLayout()

        # Map tiles path
        map_controls_layout.addWidget(QLabel("Tiles Path:"))
        self.tiles_path_input = QLineEdit()
        self.tiles_path_input.setText("MDRS_2025-11-25_163543/Bing Satellite")
        self.tiles_path_input.setMinimumWidth(300)
        map_controls_layout.addWidget(self.tiles_path_input)

        # Load tiles button
        load_tiles_button = QPushButton("Load Map Tiles")
        load_tiles_button.clicked.connect(self.load_map_tiles)
        map_controls_layout.addWidget(load_tiles_button)

        # Show overlay checkbox
        self.overlay_checkbox = QCheckBox("Show Overlay")
        self.overlay_checkbox.setChecked(True)
        self.overlay_checkbox.stateChanged.connect(self.toggle_overlay)
        map_controls_layout.addWidget(self.overlay_checkbox)

        # Overlay transparency control
        map_controls_layout.addWidget(QLabel("Overlay Alpha:"))
        self.alpha_slider = QSlider(Qt.Horizontal)
        self.alpha_slider.setMinimum(0)
        self.alpha_slider.setMaximum(100)
        self.alpha_slider.setValue(70)
        self.alpha_slider.valueChanged.connect(self.change_overlay_alpha)
        map_controls_layout.addWidget(self.alpha_slider)

        map_controls_layout.addStretch()
        layout.addLayout(map_controls_layout)

        # Instructions
        instructions = QLabel(
            "Controls: Left-drag to rotate | Right/Middle-drag to pan | Mouse wheel to zoom | Adjust sliders for point size and overlay transparency"
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
                max_points = 1000000  # VBOs can handle much more
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
        actual_size = value / 10.0  # Convert slider value to actual size (0.1 to 10.0)
        self.gl_widget.set_point_size(actual_size)
        self.size_label.setText(f"{actual_size:.1f}")

    def load_map_tiles(self):
        """Load map tiles from the specified path"""
        tiles_path = self.tiles_path_input.text()

        if not os.path.exists(tiles_path):
            self.info_label.setText(f"Error: Tiles path not found: {tiles_path}")
            return

        try:
            self.gl_widget.load_map_tiles(tiles_path, zoom_level=15)
            self.info_label.setText(f"Map tiles loaded from: {tiles_path}")
        except Exception as e:
            self.info_label.setText(f"Error loading map tiles: {str(e)}")

    def toggle_overlay(self, state):
        """Toggle map overlay visibility"""
        self.gl_widget.toggle_overlay(state == Qt.CheckState.Checked.value)

    def change_overlay_alpha(self, value):
        """Update overlay transparency"""
        alpha = value / 100.0
        self.gl_widget.set_overlay_alpha(alpha)


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