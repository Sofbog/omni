
import omni.ext
import omni.ui as ui
import omni.usd
import asyncio
from pxr import Gf, UsdGeom, Sdf, UsdShade, Vt, UsdGeom
import random

# This extension creates a bouncing sphere in the scene and provides a simple UI to control the simulation.
class BouncingSphereExtension(omni.ext.IExt):
    def on_startup(self, ext_id):
        self._stage = omni.usd.get_context().get_stage()  # Get the current USD stage
        
        # UI setup
        self._window = ui.Window("Bouncing Sphere Controller", width=300, height=300)
        self._running = False
        self._height = 20.0  # Initial height of the sphere (meters above the ground)
        self._velocity = 0.0  # Initial velocity (m/s)
        self._gravity = -9.81  # Gravity constant (m/s^2)
        self._time_step = 0.016  # Time step for the simulation (60 FPS)
        self._elasticity = 0.7  # Coefficient of restitution (bounciness)
        self._timer = None
        self._sphere = None

        with self._window.frame:
            with ui.VStack():
                self._label = ui.Label(f"Height: {self._height:.2f} meters")
                
                with ui.HStack(style={"justify-content": "space-around"}):
                    ui.Button("Start", clicked_fn=self.start_simulation)
                    ui.Button("Stop", clicked_fn=self.stop_simulation)
                    ui.Button("Reset", clicked_fn=self.reset_simulation)
                    ui.Button("Change S color", clicked_fn=self.change_sphere_color)
                    ui.Button("Change G color", clicked_fn=self.change_ground_color)
                                        

                
    def on_shutdown(self):
        if self._timer:
            self._timer.cancel()

    def create_sphere(self):
        """Creates a sphere in the scene and initializes its position."""
        if self._sphere:
            self._stage.RemovePrim(self._sphere.GetPath())
        
        sphere_prim_path = Sdf.Path("/World/bouncing_sphere")
        self._sphere = UsdGeom.Sphere.Define(self._stage, sphere_prim_path)
        self._sphere.GetRadiusAttr().Set(1.0)  # Sphere radius is 1 meter
        self.xform = UsdGeom.XformCommonAPI(self._sphere.GetPrim())
        self.xform.SetTranslate((0, self._height, 0))

    def create_ground_plane(self):
        """Creates a visible ground plane for the sphere to bounce on."""
        plane_prim_path = Sdf.Path("/World/ground_plane")
        self._plane = UsdGeom.Mesh.Define(self._stage, plane_prim_path)
        self._plane.CreateDoubleSidedAttr(True)

        # Define a quad for the plane that is large enough and positioned correctly
        self._plane.CreateFaceVertexCountsAttr([4])
        self._plane.CreateFaceVertexIndicesAttr([0, 1, 2, 3])
        self._plane.CreatePointsAttr([(-10, -0.7, 10), (10, -0.7, 10), (10, -0.7, -10), (-10, -0.7, -10)])

        # Normals for proper lighting
        self._plane.CreateNormalsAttr(Vt.Vec3fArray(4, [0,1,0]))  # Upward facing normals
        # Material
        self._plane.GetPrim().GetReferences().AddReference('/World/Looks/Asphalt')
        
    def change_sphere_color(self):
        """Changes the color of the sphere."""
        if self._sphere:
            r = random.random()
            g = random.random()
            b = random.random()
            shader = UsdShade.Shader.Define(self._stage, Sdf.Path("/World/bouncing_sphere/color_shader"))
            shader.CreateIdAttr("UsdPreviewSurface")
            shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(r, g, b))  # Random color

            material = UsdShade.Material.Define(self._stage, Sdf.Path("/World/bouncing_sphere/material"))
            material.CreateSurfaceOutput().ConnectToSource(shader, "surface")

            UsdShade.MaterialBindingAPI(self._stage.GetPrimAtPath("/World/bouncing_sphere")).Bind(material)
    
    def change_ground_color(self):
        """Changes the color of the ground plane."""
        if self._plane:
            r = random.random()
            g = random.random()
            b = random.random()

            # Create a shader
            shader = UsdShade.Shader.Define(self._stage, Sdf.Path("/World/ground_plane/color_shader"))
            shader.CreateIdAttr("UsdPreviewSurface")
            shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(r, g, b))

            # Create a material
            material = UsdShade.Material.Define(self._stage, Sdf.Path("/World/ground_plane/color_material"))

            # Bind the shader to the material
            material.CreateSurfaceOutput().ConnectToSource(shader, 'surface')

            # Bind the material to the ground plane
            UsdShade.MaterialBindingAPI(self._plane).Bind(material)
        
    
    def start_simulation(self):
        self.create_sphere()
        self.create_ground_plane()
          # Ensure sphere is created/recreated when starting
        if not self._running:
            self._running = True
            self._timer = asyncio.ensure_future(self.run_simulation())

    def stop_simulation(self):
        self._running = False

    def reset_simulation(self):
        # Stop any running simulation first
        self._running = False
        
        # Cancel any ongoing timer to ensure no pending tasks are executed
        if self._timer:
            self._timer.cancel()
            self._timer = None
        
        # Remove the sphere from the scene if it exists
        if self._sphere:
            self._stage.RemovePrim(self._sphere.GetPath())
            self._sphere = None
        # Remove the plane from the scene if it exists
        if self._plane:
            self._stage.RemovePrim(self._plane.GetPath())
            self._plane = None
        
        # Reset physics and simulation parameters to their initial values
        self._height = 20.0  # or any other default starting height
        self._velocity = 0.0  # Reset velocity to zero
        self._label.text = "Sphere and plane removed - Simulation reset"



    async def run_simulation(self):
        while self._running:
            await asyncio.sleep(self._time_step)
            self._velocity += self._gravity * self._time_step
            self._height += self._velocity * self._time_step

            if self._height <= 0:
                self._height = -self._height * self._elasticity
                self._velocity = -self._velocity * self._elasticity

            self.xform.SetTranslate((0, self._height, 0))
            self._label.text = f"Height: {self._height:.2f} meters"