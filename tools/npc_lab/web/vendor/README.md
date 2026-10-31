# Optional GLB viewer dependency

Three.js **0.187.0**, from the official npm `three` package. Only the core/module build, GLTFLoader and its BufferGeometryUtils/SkeletonUtils dependencies are included. The original MIT [LICENSE](LICENSE) is retained. Exact source tarball, verified npm SHA-512 integrity and final file SHA-256 hashes are recorded in [manifest.json](manifest.json).

Two import-path rewrites make the loader/utilities work as local browser modules without an import map, CDN or npm install. One upstream indentation whitespace issue was normalized; no semantic implementation changes were made. The lab loads these modules only when a local GLB is configured, and limits presentation work in `../stage.js`. This vendor folder contains code, not Skyrim character assets or voice weights.
