/** CSS 3D Double Helix Memory Visualization */
function initDNAHelix(containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;
  container.innerHTML = '';
  // Create two helix containers
  function createStrand(colorClass) {
    const strand = document.createElement('div');
    strand.className = 'dna-strand relative mx-auto';
    strand.style.cssText = 'width:180px;height:200px;transform-style:preserve-3d;perspective:600px';
    for (let i = 0; i < 16; i++) {
      const rung = document.createElement('div');
      const angle = i * 22.5;
      rung.className = `absolute w-4 h-4 rounded-full ${colorClass} opacity-80`;
      rung.style.cssText = `
        left:50%; top:${i * 12}px;
        transform: translateX(-50%) rotateY(${angle}deg) translateZ(30px);
        transition: transform 0.5s, opacity 0.5s;
      `;
      strand.appendChild(rung);
    }
    return strand;
  }

  const wrapper = document.createElement('div');
  wrapper.className = 'relative mx-auto';
  wrapper.style.cssText = 'width:180px;height:200px;animation:helixRotate 12s linear infinite;transform-style:preserve-3d;';

  // Spinner overlay using CSS animation keyframes
  const style = document.createElement('style');
  style.textContent = `
    @keyframes helixRotate {
      from { transform: rotateY(0deg); }
      to { transform: rotateY(360deg); }
    }
  `;
  document.head.appendChild(style);

  const leftStrand = createStrand('bg-blue-500');
  leftStrand.style.position = 'absolute'; leftStrand.style.top = '0'; leftStrand.style.left = '0';
  leftStrand.style.transform = 'translateX(-12px)';

  const rightStrand = createStrand('bg-purple-500');
  rightStrand.style.position = 'absolute'; rightStrand.style.top = '0'; rightStrand.style.right = '0';
  rightStrand.style.transform = 'translateX(12px)';
  rightStrand.style.animation = 'helixRotate 12s linear infinite reverse';

  // Rung connectors
  const connectors = document.createElement('div');
  connectors.style.cssText = 'position:absolute;left:0;top:0;width:100%;height:100%;';
  for(let i=0;i<16;i++){
    const line = document.createElement('div');
    line.style.cssText = `position:absolute;left:50%;top:${i*12+8}px;width:60%;height:1px;background:rgba(255,255,255,0.15);transform:translateX(-50%);`;
    connectors.appendChild(line);
  }

  wrapper.appendChild(leftStrand);
  wrapper.appendChild(rightStrand);
  wrapper.appendChild(connectors);
  container.appendChild(wrapper);

  return {
    updateColors: (pending, approved, contra) => {
      // shift colors based on memory stats
      const leftDots = leftStrand.querySelectorAll('.rounded-full');
      const rightDots = rightStrand.querySelectorAll('.rounded-full');
      const total = pending+approved+contra || 1;
      const pPending = pending/total, pApproved = approved/total, pContra = contra/total;
      leftDots.forEach((dot,i) => {
        if (i/total < pPending) dot.className = 'absolute w-4 h-4 rounded-full bg-amber-500 opacity-80';
        else if (i/total < pPending+pApproved) dot.className = 'absolute w-4 h-4 rounded-full bg-blue-500 opacity-80';
        else dot.className = 'absolute w-4 h-4 rounded-full bg-red-400 opacity-80';
      });
      rightDots.forEach((dot,i) => {
        if (i/total < pPending) dot.className = 'absolute w-4 h-4 rounded-full bg-amber-500 opacity-80';
        else if (i/total < pPending+pApproved) dot.className = 'absolute w-4 h-4 rounded-full bg-blue-500 opacity-80';
        else dot.className = 'absolute w-4 h-4 rounded-full bg-red-400 opacity-80';
      });
    }
  };
}
