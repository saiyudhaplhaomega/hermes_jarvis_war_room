/** Three.js 3D Agent Constellation Map — Global Scope Version */
(function(){
  let scene, camera, renderer, group, animFrame;
  let orbMeshes = [], connMeshes = [];

  function getContainerH(el){ return el ? (el.offsetHeight || 240) : 240; }

  window.init3D = function(containerId) {
    const container = document.getElementById(containerId);
    if (!container) { console.error('No container for 3D'); return; }
    if (typeof THREE === 'undefined') {
      container.innerHTML = '<div style="height:100%;display:flex;align-items:center;justify-content:center;color:#6b7280;font:12px JetBrains Mono, monospace;text-align:center;padding:16px">3D constellation unavailable<br><span style="font-size:10px">Three.js CDN did not load; 2D agent list remains active.</span></div>';
      return null;
    }
    const h = getContainerH(container);

    scene = new THREE.Scene();
    scene.background = new THREE.Color('#0b0f19');

    camera = new THREE.PerspectiveCamera(75, container.offsetWidth / Math.max(h,1), 0.1, 1000);
    camera.position.z = 6;

    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
    renderer.setSize(container.offsetWidth, h);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.innerHTML = '';
    container.appendChild(renderer.domElement);

    group = new THREE.Group();

    // Lights
    const ambient = new THREE.AmbientLight(0xffffff, 0.6);
    scene.add(ambient);
    const dir = new THREE.DirectionalLight(0xffffff, 0.8);
    dir.position.set(5, 5, 5);
    scene.add(dir);

    // Starfield
    const starGeo = new THREE.BufferGeometry();
    const starCount = 200;
    const positions = new Float32Array(starCount * 3);
    for(let i=0; i<starCount*3; i++){
      positions[i] = (Math.random()-0.5) * 40;
    }
    starGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    const starMat = new THREE.PointsMaterial({ color:0xffffff, size:0.05, transparent:true, opacity:0.7 });
    scene.add(new THREE.Points(starGeo, starMat));

    scene.add(group);
    animate();
    return { camera, scene, renderer };
  };

  window.update3D = function(data){
    const agents = data || [];
    // clear old orbs / connections
    orbMeshes.forEach(m => { if(m && group) group.remove(m); });
    connMeshes.forEach(m => { if(m && group) group.remove(m); });
    orbMeshes = [];
    connMeshes = [];

    const n = Math.min(agents.length, 12);
    for(let i=0; i<n; i++){
      const a = agents[i];
      const color = new THREE.Color(a.color || '#6b7280');
      const geo = new THREE.SphereGeometry(0.2 + (a.score||0)*0.005, 32, 32);
      const mat = new THREE.MeshStandardMaterial({ color, emissive: color, emissiveIntensity: 0.4 });
      const mesh = new THREE.Mesh(geo, mat);
      const phi = Math.acos(-1 + (2*i)/Math.max(n,1));
      const theta = Math.sqrt(Math.max(n,1) * Math.PI) * phi;
      const r = 3 + Math.random()*0.5;
      mesh.position.set(r*Math.cos(theta)*Math.sin(phi), r*Math.sin(theta)*Math.sin(phi), r*Math.cos(phi));
      mesh.userData = a;
      group.add(mesh);
      orbMeshes.push(mesh);

      // glow ring
      const ringGeo = new THREE.TorusGeometry(0.25, 0.02, 12, 48);
      const ringMat = new THREE.MeshBasicMaterial({ color, transparent:true, opacity:0.35 });
      const ring = new THREE.Mesh(ringGeo, ringMat);
      ring.position.copy(mesh.position);
      ring.rotation.x = Math.random();
      group.add(ring);
      orbMeshes.push(ring);
    }

    // connections between nearby orbs
    for(let i=0; i<n; i++){
      for(let j=i+1; j<n; j++){
        const p1 = orbMeshes[i*2]?.position, p2 = orbMeshes[j*2]?.position;
        if(!p1 || !p2) continue;
        const dist = p1.distanceTo(p2);
        if(dist < 4.5){
          const points = [p1, p2];
          const geo = new THREE.BufferGeometry().setFromPoints(points);
          const mat = new THREE.LineBasicMaterial({ color:0xffffff, transparent:true, opacity:0.15 });
          const line = new THREE.Line(geo, mat);
          group.add(line);
          connMeshes.push(line);
        }
      }
    }
  };

  function animate() {
    animFrame = requestAnimationFrame(animate);
    if(!group || !renderer || !camera) return;
    group.rotation.y += 0.001;
    group.rotation.x += 0.0003;
    // pulse rings
    orbMeshes.forEach((m,i) => {
      if(m && m.geometry && m.geometry.type === 'TorusGeometry'){
        m.rotation.z += 0.01;
        const s = 1 + Math.sin(Date.now()*0.003 + i)*0.08;
        m.scale.set(s,s,s);
      }
    });
    renderer.render(scene, camera);
  }

  window.dispose3D = function(){
    if(animFrame) cancelAnimationFrame(animFrame);
    if(renderer) renderer.dispose();
  };
})();
