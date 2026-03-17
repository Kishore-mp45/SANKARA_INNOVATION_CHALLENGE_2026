/**
 * PatientPath AI — 3D Hospital Navigation
 * =========================================
 * Three.js-based indoor navigation showing department layout,
 * current/next department highlights, and navigation path.
 */

(function () {
    'use strict';

    // ── Department layout config ────────────────────────────────────────────────
    var DEPARTMENTS = [
        { key: 'entrance',          label: 'Entrance',           x: -24, color: 0x64748b, isEntrance: true },
        { key: 'registration',      label: 'Registration',       x: -18, color: 0x3b82f6 },
        { key: 'vision_lab',        label: 'Vision Lab',         x: -12, color: 0x3b82f6 },
        { key: 'dilation_hall',     label: 'Dilation Hall',      x:  -6, color: 0x3b82f6 },
        { key: 'consultation',      label: 'Consultation',       x:   0, color: 0x3b82f6 },
        { key: 'diagnostics',       label: 'Diagnostics',        x:   6, color: 0x3b82f6 },
        { key: 'pharmacy',          label: 'Pharmacy',           x:  12, color: 0x3b82f6 },
        { key: 'billing_insurance', label: 'Billing & Insurance', x: 18, color: 0x3b82f6 }
    ];

    var ROOM_WIDTH  = 4.8;
    var ROOM_DEPTH  = 5;
    var ROOM_HEIGHT = 3;
    var CORRIDOR_Z  = -4;  // corridor is in front of rooms
    var CORRIDOR_DEPTH = 2;

    var COLOR_NORMAL    = 0x3b82f6;
    var COLOR_CURRENT   = 0x22c55e;
    var COLOR_NEXT      = 0xef4444;
    var COLOR_COMPLETED = 0x10b981;
    var COLOR_PATH      = 0xeab308;
    var COLOR_ENTRANCE  = 0x64748b;
    var COLOR_FLOOR     = 0x1e293b;
    var COLOR_CORRIDOR  = 0x334155;
    var COLOR_WALL      = 0x475569;

    // ── State ───────────────────────────────────────────────────────────────────
    var scene, camera, renderer, controls;
    var roomMeshes = {};   // key -> mesh
    var labelSprites = {}; // key -> sprite
    var pathLine = null;
    var arrowHelpers = [];
    var currentDept = null;
    var nextDept = null;

    // ── Init ────────────────────────────────────────────────────────────────────
    function init() {
        var canvas = document.getElementById('three-canvas');
        if (!canvas) return;

        // Scene
        scene = new THREE.Scene();
        scene.background = new THREE.Color(0x0f172a);
        scene.fog = new THREE.Fog(0x0f172a, 40, 80);

        // Camera
        var aspect = canvas.clientWidth / canvas.clientHeight;
        camera = new THREE.PerspectiveCamera(50, aspect, 0.1, 200);
        camera.position.set(0, 22, 28);
        camera.lookAt(0, 0, 0);

        // Renderer
        renderer = new THREE.WebGLRenderer({ canvas: canvas, antialias: true });
        renderer.setSize(canvas.clientWidth, canvas.clientHeight);
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        renderer.shadowMap.enabled = true;
        renderer.shadowMap.type = THREE.PCFSoftShadowMap;

        // Lights
        var ambient = new THREE.AmbientLight(0xffffff, 0.4);
        scene.add(ambient);

        var dirLight = new THREE.DirectionalLight(0xffffff, 0.7);
        dirLight.position.set(10, 20, 15);
        dirLight.castShadow = true;
        dirLight.shadow.mapSize.width = 1024;
        dirLight.shadow.mapSize.height = 1024;
        scene.add(dirLight);

        var pointLight = new THREE.PointLight(0x38bdf8, 0.3, 60);
        pointLight.position.set(0, 10, 0);
        scene.add(pointLight);

        // Build scene
        buildFloor();
        buildCorridor();
        buildRooms();
        buildCorridorWalls();

        // Orbit controls (manual minimal implementation)
        setupControls(canvas);

        // Handle resize
        window.addEventListener('resize', onResize);

        // Start render loop
        animate();

        // Fetch patient data
        fetchNavData();
        setInterval(fetchNavData, 15000);
    }

    // ── Build floor ─────────────────────────────────────────────────────────────
    function buildFloor() {
        var geo = new THREE.PlaneGeometry(60, 20);
        var mat = new THREE.MeshStandardMaterial({ color: COLOR_FLOOR, roughness: 0.9 });
        var floor = new THREE.Mesh(geo, mat);
        floor.rotation.x = -Math.PI / 2;
        floor.position.y = -0.01;
        floor.receiveShadow = true;
        scene.add(floor);

        // Grid helper for visual depth
        var grid = new THREE.GridHelper(60, 30, 0x1e3a5f, 0x1e3a5f);
        grid.position.y = 0;
        grid.material.opacity = 0.15;
        grid.material.transparent = true;
        scene.add(grid);
    }

    // ── Build corridor ──────────────────────────────────────────────────────────
    function buildCorridor() {
        var totalWidth = DEPARTMENTS[DEPARTMENTS.length - 1].x - DEPARTMENTS[0].x + ROOM_WIDTH + 4;
        var geo = new THREE.BoxGeometry(totalWidth, 0.08, CORRIDOR_DEPTH);
        var mat = new THREE.MeshStandardMaterial({ color: COLOR_CORRIDOR, roughness: 0.8 });
        var corridor = new THREE.Mesh(geo, mat);
        var centerX = (DEPARTMENTS[0].x + DEPARTMENTS[DEPARTMENTS.length - 1].x) / 2;
        corridor.position.set(centerX, 0.04, CORRIDOR_Z);
        corridor.receiveShadow = true;
        scene.add(corridor);

        // Corridor center line (dashed)
        var points = [
            new THREE.Vector3(DEPARTMENTS[0].x - 3, 0.1, CORRIDOR_Z),
            new THREE.Vector3(DEPARTMENTS[DEPARTMENTS.length - 1].x + 3, 0.1, CORRIDOR_Z)
        ];
        var lineGeo = new THREE.BufferGeometry().setFromPoints(points);
        var lineMat = new THREE.LineDashedMaterial({ color: 0x94a3b8, dashSize: 0.5, gapSize: 0.3, opacity: 0.4, transparent: true });
        var line = new THREE.Line(lineGeo, lineMat);
        line.computeLineDistances();
        scene.add(line);
    }

    // ── Build rooms ─────────────────────────────────────────────────────────────
    function buildRooms() {
        DEPARTMENTS.forEach(function (dept) {
            // Room box
            var geo = new THREE.BoxGeometry(ROOM_WIDTH, ROOM_HEIGHT, ROOM_DEPTH);
            var mat = new THREE.MeshStandardMaterial({
                color: dept.isEntrance ? COLOR_ENTRANCE : dept.color,
                roughness: 0.6,
                metalness: 0.1,
                transparent: true,
                opacity: 0.85
            });
            var mesh = new THREE.Mesh(geo, mat);
            mesh.position.set(dept.x, ROOM_HEIGHT / 2, 0);
            mesh.castShadow = true;
            mesh.receiveShadow = true;
            scene.add(mesh);
            roomMeshes[dept.key] = mesh;

            // Roof edge highlight
            var edgeGeo = new THREE.BoxGeometry(ROOM_WIDTH + 0.1, 0.08, ROOM_DEPTH + 0.1);
            var edgeMat = new THREE.MeshBasicMaterial({ color: dept.isEntrance ? COLOR_ENTRANCE : dept.color });
            var edge = new THREE.Mesh(edgeGeo, edgeMat);
            edge.position.set(dept.x, ROOM_HEIGHT + 0.04, 0);
            scene.add(edge);

            // Door marker (small box on corridor side)
            var doorGeo = new THREE.BoxGeometry(0.8, 1.6, 0.15);
            var doorMat = new THREE.MeshStandardMaterial({ color: 0x94a3b8, roughness: 0.4 });
            var door = new THREE.Mesh(doorGeo, doorMat);
            door.position.set(dept.x, 0.8, -ROOM_DEPTH / 2 - 0.07);
            scene.add(door);

            // Label sprite
            var sprite = makeTextSprite(dept.label, dept.isEntrance ? COLOR_ENTRANCE : dept.color);
            sprite.position.set(dept.x, ROOM_HEIGHT + 1.0, 0);
            scene.add(sprite);
            labelSprites[dept.key] = sprite;
        });
    }

    // ── Corridor walls ──────────────────────────────────────────────────────────
    function buildCorridorWalls() {
        var startX = DEPARTMENTS[0].x - ROOM_WIDTH / 2 - 2;
        var endX = DEPARTMENTS[DEPARTMENTS.length - 1].x + ROOM_WIDTH / 2 + 2;
        var width = endX - startX;
        var centerX = (startX + endX) / 2;

        // Back wall (behind corridor, opposite side of rooms)
        var wallGeo = new THREE.BoxGeometry(width, 3, 0.12);
        var wallMat = new THREE.MeshStandardMaterial({ color: COLOR_WALL, roughness: 0.9, transparent: true, opacity: 0.4 });
        var wall = new THREE.Mesh(wallGeo, wallMat);
        wall.position.set(centerX, 1.5, CORRIDOR_Z - CORRIDOR_DEPTH / 2);
        scene.add(wall);
    }

    // ── Text sprite helper ──────────────────────────────────────────────────────
    function makeTextSprite(text, hexColor) {
        var canvas2d = document.createElement('canvas');
        canvas2d.width = 512;
        canvas2d.height = 128;
        var ctx = canvas2d.getContext('2d');

        ctx.fillStyle = 'transparent';
        ctx.fillRect(0, 0, 512, 128);

        ctx.font = 'bold 36px Arial, sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';

        // Outline
        ctx.strokeStyle = '#000';
        ctx.lineWidth = 4;
        ctx.strokeText(text, 256, 64);

        // Fill
        var r = (hexColor >> 16) & 0xff;
        var g = (hexColor >> 8) & 0xff;
        var b = hexColor & 0xff;
        ctx.fillStyle = 'rgb(' + r + ',' + g + ',' + b + ')';
        ctx.fillText(text, 256, 64);

        var texture = new THREE.CanvasTexture(canvas2d);
        texture.needsUpdate = true;

        var spriteMat = new THREE.SpriteMaterial({ map: texture, transparent: true, depthTest: false });
        var sprite = new THREE.Sprite(spriteMat);
        sprite.scale.set(6, 1.5, 1);
        return sprite;
    }

    // ── Update highlight colors ─────────────────────────────────────────────────
    function updateHighlights(currentKey, nextKey, journeySteps) {
        var completedKeys = {};
        if (journeySteps) {
            journeySteps.forEach(function (s) {
                if (s.status === 'completed') completedKeys[s.zone_key] = true;
            });
        }

        DEPARTMENTS.forEach(function (dept) {
            var mesh = roomMeshes[dept.key];
            var sprite = labelSprites[dept.key];
            if (!mesh) return;

            var color;
            if (dept.isEntrance) {
                color = COLOR_ENTRANCE;
            } else if (dept.key === currentKey) {
                color = COLOR_CURRENT;
            } else if (dept.key === nextKey) {
                color = COLOR_NEXT;
            } else if (completedKeys[dept.key]) {
                color = COLOR_COMPLETED;
            } else {
                color = COLOR_NORMAL;
            }

            mesh.material.color.setHex(color);

            // Pulse current room
            if (dept.key === currentKey) {
                mesh.material.emissive = new THREE.Color(COLOR_CURRENT);
                mesh.material.emissiveIntensity = 0.2;
            } else if (dept.key === nextKey) {
                mesh.material.emissive = new THREE.Color(COLOR_NEXT);
                mesh.material.emissiveIntensity = 0.15;
            } else {
                mesh.material.emissive = new THREE.Color(0x000000);
                mesh.material.emissiveIntensity = 0;
            }

            // Update label sprite color
            if (sprite) {
                scene.remove(sprite);
                var newSprite = makeTextSprite(dept.label, color);
                newSprite.position.copy(sprite.position);
                scene.add(newSprite);
                labelSprites[dept.key] = newSprite;
            }
        });

        // Draw navigation path
        drawPath(currentKey, nextKey);
    }

    // ── Draw navigation path ────────────────────────────────────────────────────
    function drawPath(fromKey, toKey) {
        // Remove old path
        if (pathLine) { scene.remove(pathLine); pathLine = null; }
        arrowHelpers.forEach(function (a) { scene.remove(a); });
        arrowHelpers = [];

        if (!fromKey || !toKey) return;

        var fromDept = DEPARTMENTS.find(function (d) { return d.key === fromKey; });
        var toDept = DEPARTMENTS.find(function (d) { return d.key === toKey; });
        if (!fromDept || !toDept) return;

        var y = 0.15;
        var points = [
            new THREE.Vector3(fromDept.x, y, -ROOM_DEPTH / 2 - 0.2),  // exit door
            new THREE.Vector3(fromDept.x, y, CORRIDOR_Z),               // corridor
            new THREE.Vector3(toDept.x,   y, CORRIDOR_Z),               // walk along corridor
            new THREE.Vector3(toDept.x,   y, -ROOM_DEPTH / 2 - 0.2)    // enter next door
        ];

        // Smooth curve through points
        var curve = new THREE.CatmullRomCurve3(points, false, 'chordal');
        var curvePoints = curve.getPoints(60);

        var geo = new THREE.BufferGeometry().setFromPoints(curvePoints);
        var mat = new THREE.LineBasicMaterial({ color: COLOR_PATH, linewidth: 2 });
        pathLine = new THREE.Line(geo, mat);
        scene.add(pathLine);

        // Arrows along the path
        var numArrows = 5;
        for (var i = 1; i <= numArrows; i++) {
            var t = i / (numArrows + 1);
            var pos = curve.getPointAt(t);
            var tangent = curve.getTangentAt(t).normalize();
            var arrow = new THREE.ArrowHelper(
                tangent,
                pos,
                0.6,
                COLOR_PATH,
                0.35,
                0.2
            );
            scene.add(arrow);
            arrowHelpers.push(arrow);
        }

        // Pulsing glow spheres at endpoints
        var startGlow = new THREE.Mesh(
            new THREE.SphereGeometry(0.3, 16, 16),
            new THREE.MeshBasicMaterial({ color: COLOR_CURRENT, transparent: true, opacity: 0.7 })
        );
        startGlow.position.set(fromDept.x, 0.3, -ROOM_DEPTH / 2 - 0.2);
        scene.add(startGlow);
        arrowHelpers.push(startGlow);

        var endGlow = new THREE.Mesh(
            new THREE.SphereGeometry(0.3, 16, 16),
            new THREE.MeshBasicMaterial({ color: COLOR_NEXT, transparent: true, opacity: 0.7 })
        );
        endGlow.position.set(toDept.x, 0.3, -ROOM_DEPTH / 2 - 0.2);
        scene.add(endGlow);
        arrowHelpers.push(endGlow);
    }

    // ── Orbit controls (simple manual) ──────────────────────────────────────────
    function setupControls(canvas) {
        var isDragging = false;
        var isPanning = false;
        var prevX = 0, prevY = 0;
        var spherical = { theta: 0, phi: Math.PI / 4, radius: 35 };
        var target = new THREE.Vector3(0, 0, 0);

        function updateCamera() {
            var sinPhi = Math.sin(spherical.phi);
            camera.position.x = target.x + spherical.radius * sinPhi * Math.sin(spherical.theta);
            camera.position.y = target.y + spherical.radius * Math.cos(spherical.phi);
            camera.position.z = target.z + spherical.radius * sinPhi * Math.cos(spherical.theta);
            camera.lookAt(target);
        }
        updateCamera();

        canvas.addEventListener('mousedown', function (e) {
            if (e.button === 0) { isDragging = true; }
            else if (e.button === 2) { isPanning = true; }
            prevX = e.clientX;
            prevY = e.clientY;
        });

        canvas.addEventListener('mousemove', function (e) {
            var dx = e.clientX - prevX;
            var dy = e.clientY - prevY;
            prevX = e.clientX;
            prevY = e.clientY;

            if (isDragging) {
                spherical.theta -= dx * 0.005;
                spherical.phi = Math.max(0.15, Math.min(Math.PI / 2.1, spherical.phi - dy * 0.005));
                updateCamera();
            } else if (isPanning) {
                var panSpeed = spherical.radius * 0.002;
                var right = new THREE.Vector3();
                var up = new THREE.Vector3(0, 1, 0);
                camera.getWorldDirection(right);
                right.cross(up).normalize();
                target.addScaledVector(right, -dx * panSpeed);
                target.y += dy * panSpeed;
                updateCamera();
            }
        });

        window.addEventListener('mouseup', function () {
            isDragging = false;
            isPanning = false;
        });

        canvas.addEventListener('wheel', function (e) {
            e.preventDefault();
            spherical.radius = Math.max(10, Math.min(60, spherical.radius + e.deltaY * 0.03));
            updateCamera();
        }, { passive: false });

        canvas.addEventListener('contextmenu', function (e) { e.preventDefault(); });

        // Touch support
        var lastTouchDist = 0;
        canvas.addEventListener('touchstart', function (e) {
            if (e.touches.length === 1) {
                isDragging = true;
                prevX = e.touches[0].clientX;
                prevY = e.touches[0].clientY;
            } else if (e.touches.length === 2) {
                isDragging = false;
                var dx2 = e.touches[0].clientX - e.touches[1].clientX;
                var dy2 = e.touches[0].clientY - e.touches[1].clientY;
                lastTouchDist = Math.sqrt(dx2 * dx2 + dy2 * dy2);
            }
        });

        canvas.addEventListener('touchmove', function (e) {
            e.preventDefault();
            if (e.touches.length === 1 && isDragging) {
                var dx3 = e.touches[0].clientX - prevX;
                var dy3 = e.touches[0].clientY - prevY;
                prevX = e.touches[0].clientX;
                prevY = e.touches[0].clientY;
                spherical.theta -= dx3 * 0.005;
                spherical.phi = Math.max(0.15, Math.min(Math.PI / 2.1, spherical.phi - dy3 * 0.005));
                updateCamera();
            } else if (e.touches.length === 2) {
                var dx4 = e.touches[0].clientX - e.touches[1].clientX;
                var dy4 = e.touches[0].clientY - e.touches[1].clientY;
                var dist = Math.sqrt(dx4 * dx4 + dy4 * dy4);
                var delta = lastTouchDist - dist;
                spherical.radius = Math.max(10, Math.min(60, spherical.radius + delta * 0.08));
                lastTouchDist = dist;
                updateCamera();
            }
        }, { passive: false });

        canvas.addEventListener('touchend', function () {
            isDragging = false;
        });
    }

    // ── Resize handler ──────────────────────────────────────────────────────────
    function onResize() {
        var canvas = document.getElementById('three-canvas');
        if (!canvas || !renderer) return;
        var w = canvas.clientWidth;
        var h = canvas.clientHeight;
        renderer.setSize(w, h);
        camera.aspect = w / h;
        camera.updateProjectionMatrix();
    }

    // ── Animation loop ──────────────────────────────────────────────────────────
    var clock = new THREE.Clock();

    function animate() {
        requestAnimationFrame(animate);

        var t = clock.getElapsedTime();

        // Pulse current department
        if (currentDept && roomMeshes[currentDept]) {
            var pulse = 0.15 + Math.sin(t * 3) * 0.1;
            roomMeshes[currentDept].material.emissiveIntensity = pulse;
        }

        // Pulse next department
        if (nextDept && roomMeshes[nextDept]) {
            var pulse2 = 0.1 + Math.sin(t * 2.5 + 1) * 0.08;
            roomMeshes[nextDept].material.emissiveIntensity = pulse2;
        }

        // Animate path glow spheres
        arrowHelpers.forEach(function (obj) {
            if (obj.isMesh && obj.geometry.type === 'SphereGeometry') {
                obj.material.opacity = 0.5 + Math.sin(t * 4) * 0.3;
            }
        });

        renderer.render(scene, camera);
    }

    // ── Fetch patient navigation data ───────────────────────────────────────────
    function fetchNavData() {
        var patientId = sessionStorage.getItem('currentPatientId') || sessionStorage.getItem('currentUser') ||
                        localStorage.getItem('currentPatientId') || localStorage.getItem('currentUser');

        var tag = document.getElementById('patient-id-tag');
        if (!patientId) {
            if (tag) tag.innerHTML = '<i class="fas fa-exclamation-triangle"></i> No patient ID';
            return;
        }
        if (tag) tag.innerHTML = '<i class="fas fa-id-badge"></i> ' + patientId;

        var baseUrl = (typeof API_BASE !== 'undefined') ? API_BASE : '';

        fetch(baseUrl + '/patient/eta/' + patientId + '?_=' + Date.now())
            .then(function (res) {
                if (!res.ok) throw new Error('Not found');
                return res.json();
            })
            .then(function (data) {
                currentDept = data.current_zone;
                nextDept = data.next_zone;

                // Update info bar
                var curEl = document.getElementById('nav-current-dept');
                var nxtEl = document.getElementById('nav-next-dept');
                var waitEl = document.getElementById('nav-wait-time');

                if (curEl) curEl.textContent = data.current_zone_display || '--';
                if (nxtEl) nxtEl.textContent = data.next_zone_display || '--';
                if (waitEl) {
                    if (data.predicted_waiting_time !== null && data.predicted_waiting_time !== undefined) {
                        waitEl.textContent = Math.round(data.predicted_waiting_time) + ' min';
                    } else {
                        waitEl.textContent = '--';
                    }
                }

                // Update 3D highlights
                updateHighlights(currentDept, nextDept, data.journey_steps);
            })
            .catch(function (err) {
                console.warn('Navigation data fetch error:', err);
                var curEl = document.getElementById('nav-current-dept');
                if (curEl) curEl.textContent = 'Not registered yet';
                var nxtEl = document.getElementById('nav-next-dept');
                if (nxtEl) nxtEl.textContent = '--';
            });
    }

    // ── Boot ────────────────────────────────────────────────────────────────────
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
