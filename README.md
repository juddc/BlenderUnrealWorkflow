# BlenderUnrealWorkflow
Blender addon that adds tools for making game art assets easier.

## Features
* Export all meshes in a scene using the mesh's individual origins instead of the scene's origin
* Export custom convex collision (`UCX_` prefixed meshes) - see [Epic's docs](https://docs.unrealengine.com/latest/INT/Engine/Content/FBX/StaticMeshes/index.html#collision).
* Mass-rename meshes so they conform to the `UCX_Name_##` naming scheme
* Switch draw type of all `UCX_` prefixed meshes between wireframe and solid to make it easier to visualize collision meshes
* Set up a UV Project modifier with a 6-axis camera setup (UV Cube Projection) for ease of prototyping before UVs are created manually. Because this is a modifier, you can leave subsurf and other modifiers on your mesh and still get a reasonable UV map when exporting.

## TODO / Not currently implemented
* Export animation and armatures
* Export simple cube and sphere collisions
* Expose more of the FBX exporter's settings

## Screenshot
![screenshot](https://raw.githubusercontent.com/juddc/BlenderUnrealWorkflow/master/BlenderUnrealWorkflow_Screenshot.png)
