// 3D Avatar Engine - Sebax Head Unit (Solo Cabeza en Zona Izquierda)
(function () {
  const container = document.getElementById("canvas-container");
  if (!container) return;

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x070709);
  scene.fog = new THREE.FogExp2(0x070709, 0.035);

  const camera = new THREE.PerspectiveCamera(40, window.innerWidth / window.innerHeight, 0.1, 100);
  camera.position.set(0, 0, 3.4);

  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.2;
  container.appendChild(renderer.domElement);

  // Iluminacion Studio Onyx y Titanio
  const hemiLight = new THREE.HemisphereLight(0xffffff, 0x18181b, 0.95);
  scene.add(hemiLight);

  const keyLight = new THREE.DirectionalLight(0xffffff, 1.8);
  keyLight.position.set(2, 6, 4);
  keyLight.castShadow = true;
  keyLight.shadow.mapSize.width = 1024;
  keyLight.shadow.mapSize.height = 1024;
  scene.add(keyLight);

  const fillLight = new THREE.DirectionalLight(0x38bdf8, 0.75);
  fillLight.position.set(-5, 2, 3);
  scene.add(fillLight);

  const rimLight = new THREE.DirectionalLight(0x38bdf8, 1.3);
  rimLight.position.set(-2, 3, -3);
  scene.add(rimLight);

  const backLight = new THREE.DirectionalLight(0xe2e8f0, 0.8);
  backLight.position.set(0, 3, -4);
  scene.add(backLight);

  // Materiales de alta fidelidad al diseno de Sebax
  const whiteMat = new THREE.MeshStandardMaterial({
    color: 0xffffff,
    metalness: 0.05,
    roughness: 0.28,
  });

  const blackMat = new THREE.MeshStandardMaterial({
    color: 0x151619,
    metalness: 0.1,
    roughness: 0.45,
  });

  const screenMat = new THREE.MeshStandardMaterial({
    color: 0x0f1013,
    metalness: 0.15,
    roughness: 0.2,
  });

  const eyeMat = new THREE.MeshBasicMaterial({
    color: 0x52525b, // Gris suave en reposo
  });

  const eyeGlowMat = new THREE.MeshBasicMaterial({
    color: 0x38bdf8, // Celeste neon brillante al hablar
  });

  // Raiz del Personaje Sebax (Unidad de Cabeza)
  const robot = new THREE.Group();
  scene.add(robot);

  // ----------------------------------------------------
  // CABEZA CENTRADA EN EL PIVOTE (0, 0, 0)
  // ----------------------------------------------------
  const headGroup = new THREE.Group();
  headGroup.position.set(0, 0, 0);
  robot.add(headGroup);

  // Caja principal de la cabeza blanca
  const headBoxGeo = new THREE.BoxGeometry(1.4, 1.15, 0.95);
  const headBox = new THREE.Mesh(headBoxGeo, whiteMat);
  headBox.castShadow = true;
  headBox.receiveShadow = true;
  headGroup.add(headBox);

  // Marco exterior de la pantalla frontal (Bisel negro)
  const screenFrameGeo = new THREE.BoxGeometry(1.15, 0.92, 0.08);
  const screenFrame = new THREE.Mesh(screenFrameGeo, blackMat);
  screenFrame.position.set(0, -0.02, 0.46);
  screenFrame.castShadow = true;
  headGroup.add(screenFrame);

  // Pantalla interior negra
  const screenInnerGeo = new THREE.BoxGeometry(1.02, 0.78, 0.04);
  const screenInner = new THREE.Mesh(screenInnerGeo, screenMat);
  screenInner.position.set(0, -0.02, 0.49);
  headGroup.add(screenInner);

  // Ojos estilo Pixel (Dos rectangulos verticales)
  const eyeGeo = new THREE.BoxGeometry(0.14, 0.32, 0.02);
  const leftEye = new THREE.Mesh(eyeGeo, eyeMat);
  leftEye.position.set(-0.25, -0.02, 0.515);
  headGroup.add(leftEye);

  const rightEye = new THREE.Mesh(eyeGeo, eyeMat);
  rightEye.position.set(0.25, -0.02, 0.515);
  headGroup.add(rightEye);

  // Orejeras / Auriculares laterales (Izquierda y Derecha)
  function createEar(isRight) {
    const earGroup = new THREE.Group();
    const sign = isRight ? 1 : -1;
    earGroup.position.set(sign * 0.72, -0.02, 0);

    // Marco exterior blanco
    const earWhite = new THREE.Mesh(new THREE.BoxGeometry(0.12, 0.45, 0.42), whiteMat);
    earWhite.castShadow = true;
    earGroup.add(earWhite);

    // Nucleo negro interno
    const earBlack = new THREE.Mesh(new THREE.BoxGeometry(0.14, 0.32, 0.3), blackMat);
    earBlack.position.x = sign * 0.02;
    earGroup.add(earBlack);

    return earGroup;
  }
  headGroup.add(createEar(false));
  headGroup.add(createEar(true));

  // Antena asimetrica en la parte superior izquierda de la cabeza
  const antennaGroup = new THREE.Group();
  antennaGroup.position.set(0.35, 0.575, -0.05);

  const antBase = new THREE.Mesh(new THREE.BoxGeometry(0.18, 0.12, 0.18), blackMat);
  antBase.position.y = 0.06;
  antennaGroup.add(antBase);

  const antStem = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.04, 0.3, 16), whiteMat);
  antStem.position.y = 0.25;
  antennaGroup.add(antStem);

  const antTip = new THREE.Mesh(new THREE.BoxGeometry(0.16, 0.18, 0.16), blackMat);
  antTip.position.y = 0.46;
  antennaGroup.add(antTip);

  headGroup.add(antennaGroup);

  // Vistas traseras de la cabeza: Ranuras horizontales
  const backVent1 = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.08, 0.04), whiteMat);
  backVent1.position.set(0, 0.12, -0.49);
  headGroup.add(backVent1);

  const backVent2 = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.08, 0.04), whiteMat);
  backVent2.position.set(0, -0.06, -0.49);
  headGroup.add(backVent2);

  // Base / Cuello flotante minimalista en la base de la cabeza
  const baseRing = new THREE.Mesh(new THREE.CylinderGeometry(0.24, 0.28, 0.1, 24), blackMat);
  baseRing.position.y = -0.62;
  headGroup.add(baseRing);

  // Sombra de halo inferior flotante
  const shadowCanvas = document.createElement("canvas");
  shadowCanvas.width = 128;
  shadowCanvas.height = 128;
  const sCtx = shadowCanvas.getContext("2d");
  const sGrad = sCtx.createRadialGradient(64, 64, 0, 64, 64, 64);
  sGrad.addColorStop(0, "rgba(56, 189, 248, 0.35)");
  sGrad.addColorStop(0.35, "rgba(16, 185, 129, 0.15)");
  sGrad.addColorStop(1, "rgba(7, 7, 9, 0)");
  sCtx.fillStyle = sGrad;
  sCtx.fillRect(0, 0, 128, 128);
  const glowTexture = new THREE.CanvasTexture(shadowCanvas);

  const glowPlane = new THREE.Mesh(
    new THREE.PlaneGeometry(2.0, 2.0),
    new THREE.MeshBasicMaterial({ map: glowTexture, transparent: true, opacity: 0.65, depthWrite: false })
  );
  glowPlane.rotation.x = -Math.PI / 2;
  glowPlane.position.y = -0.95;
  headGroup.add(glowPlane);

  // ----------------------------------------------------
  // INTERACCION Y ANIMACION
  // ----------------------------------------------------
  let isSpeaking = false;
  let isThinking = false;
  let targetRotation = { x: 0, y: 0 };
  let currentRotation = { x: 0, y: 0 };
  let baseY = 0.0;

  // Seguimiento inteligente del cursor hacia el panel derecho
  function onPointerMove(e) {
    const clientX = e.clientX || (e.touches && e.touches[0].clientX) || 0;
    const clientY = e.clientY || (e.touches && e.touches[0].clientY) || 0;
    const normX = (clientX / window.innerWidth) * 2 - 1;
    const normY = -(clientY / window.innerHeight) * 2 + 1;

    const isMobile = window.innerWidth < 768;
    const robotCenterNormX = isMobile ? 0 : -0.48;

    // Calcular el giro relativo para que mire hacia donde esta el mouse o texto
    targetRotation.y = (normX - robotCenterNormX) * 0.48;
    targetRotation.x = -normY * 0.32;
  }
  window.addEventListener("mousemove", onPointerMove);
  window.addEventListener("touchmove", onPointerMove, { passive: true });

  // Control de tamano y posicion dinamica segun dispositivo
  function updateLayout() {
    const width = window.innerWidth;
    const height = window.innerHeight;
    const isMobile = width < 768;

    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    renderer.setSize(width, height);

    if (isMobile) {
      baseY = 0.42;
      robot.position.set(0, baseY, 0);
      camera.position.set(0, baseY, 3.4);
    } else {
      baseY = 0.05;
      const fovRad = (camera.fov * Math.PI) / 180;
      const visibleHeight = 2 * Math.tan(fovRad / 2) * 3.4;
      const visibleWidth = visibleHeight * camera.aspect;

      // Centrar la cabeza exactamente en la mitad de la columna izquierda (aprox 24% del ancho total)
      const targetX = -(visibleWidth * 0.25);
      robot.position.set(targetX, baseY, 0);
      camera.position.set(0, baseY, 3.4);
    }
  }
  window.addEventListener("resize", updateLayout);
  updateLayout();

  // Animacion continua
  const clock = new THREE.Clock();

  function animate() {
    requestAnimationFrame(animate);
    const time = clock.getElapsedTime();

    // Rotacion suave con amortiguacion
    currentRotation.x += (targetRotation.x - currentRotation.x) * 0.08;
    currentRotation.y += (targetRotation.y - currentRotation.y) * 0.08;

    headGroup.rotation.y = currentRotation.y;
    headGroup.rotation.x = currentRotation.x;

    // Flotacion y respiracion ritmica
    const bob = Math.sin(time * 2.2) * 0.035;
    robot.position.y = baseY + bob;

    // Parpadeo periodico natural
    const blinkCycle = Math.sin(time * 1.3);
    if (blinkCycle > 0.982) {
      leftEye.scale.y = 0.1;
      rightEye.scale.y = 0.1;
    } else {
      leftEye.scale.y = 1;
      rightEye.scale.y = 1;
    }

    // Estados de expresion
    if (isSpeaking) {
      const speech = Math.sin(time * 16);
      headGroup.position.y = Math.abs(speech) * 0.035;
      leftEye.material = eyeGlowMat;
      rightEye.material = eyeGlowMat;
      leftEye.scale.y = 0.6 + Math.abs(speech) * 0.6;
      rightEye.scale.y = 0.6 + Math.abs(speech) * 0.6;
    } else if (isThinking) {
      headGroup.rotation.z = Math.sin(time * 4) * 0.05;
      leftEye.material = eyeMat;
      rightEye.material = eyeMat;
    } else {
      headGroup.position.y = 0;
      headGroup.rotation.z = 0;
      leftEye.material = eyeMat;
      rightEye.material = eyeMat;
    }

    renderer.render(scene, camera);
  }

  animate();

  window.avatar = {
    setSpeaking: (val) => { isSpeaking = val; },
    setThinking: (val) => { isThinking = val; }
  };
})();
