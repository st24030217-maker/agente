// 3D Avatar Engine - Modelo Fiel al Personaje Minimalista Blanco y Negro
(function () {
  const container = document.getElementById("canvas-container");
  if (!container) return;

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x09090b);
  scene.fog = new THREE.FogExp2(0x09090b, 0.035);

  const isMobile = window.innerWidth < 768;
  const camera = new THREE.PerspectiveCamera(40, window.innerWidth / window.innerHeight, 0.1, 100);
  camera.position.set(0, 0.4, isMobile ? 5.8 : 4.6);

  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.15;
  container.appendChild(renderer.domElement);

  // Iluminación Studio Onyx & Titanio
  const hemiLight = new THREE.HemisphereLight(0xffffff, 0x18181b, 0.85);
  scene.add(hemiLight);

  const keyLight = new THREE.DirectionalLight(0xffffff, 1.6);
  keyLight.position.set(4, 8, 5);
  keyLight.castShadow = true;
  keyLight.shadow.mapSize.width = 1024;
  keyLight.shadow.mapSize.height = 1024;
  keyLight.shadow.camera.near = 0.5;
  keyLight.shadow.camera.far = 20;
  keyLight.shadow.camera.left = -3;
  keyLight.shadow.camera.right = 3;
  keyLight.shadow.camera.top = 3;
  keyLight.shadow.camera.bottom = -3;
  keyLight.shadow.bias = -0.0005;
  scene.add(keyLight);

  const fillLight = new THREE.DirectionalLight(0x38bdf8, 0.55);
  fillLight.position.set(-4, 3, 2);
  scene.add(fillLight);

  const backLight = new THREE.DirectionalLight(0xe2e8f0, 1.1);
  backLight.position.set(0, 4, -4);
  scene.add(backLight);

  // Sombra de Piso Suave Studio
  const floorGeo = new THREE.PlaneGeometry(20, 20);
  const floorMat = new THREE.ShadowMaterial({ opacity: 0.35 });
  const floor = new THREE.Mesh(floorGeo, floorMat);
  floor.rotation.x = -Math.PI / 2;
  floor.position.y = -1.65;
  floor.receiveShadow = true;
  scene.add(floor);

  // Materiales de alta fidelidad al diseño
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
    color: 0x111215,
    metalness: 0.15,
    roughness: 0.2,
  });

  const eyeMat = new THREE.MeshBasicMaterial({
    color: 0x52525b, // Gris pixelado suave como en la foto frontal
  });

  const eyeGlowMat = new THREE.MeshBasicMaterial({
    color: 0x38bdf8, // Ojos celestes sutiles al hablar
  });

  // Raíz del Personaje
  const robot = new THREE.Group();
  robot.position.y = 0.15;
  scene.add(robot);

  // ----------------------------------------------------
  // CABEZA
  // ----------------------------------------------------
  const headGroup = new THREE.Group();
  headGroup.position.y = 0.55;
  robot.add(headGroup);

  // Caja principal de la cabeza (blanca con bordes redondeados)
  const headBoxGeo = new THREE.BoxGeometry(1.4, 1.15, 0.95);
  const headBox = new THREE.Mesh(headBoxGeo, whiteMat);
  headBox.castShadow = true;
  headBox.receiveShadow = true;
  headGroup.add(headBox);

  // Marco de la pantalla frontal (Bisel negro alrededor de la pantalla)
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

  // Ojos estilo Pixel (Dos rectángulos verticales)
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

    // Marco exterior blanco escalonado
    const earWhite = new THREE.Mesh(new THREE.BoxGeometry(0.12, 0.45, 0.42), whiteMat);
    earWhite.castShadow = true;
    earGroup.add(earWhite);

    // Núcleo negro interno
    const earBlack = new THREE.Mesh(new THREE.BoxGeometry(0.14, 0.32, 0.3), blackMat);
    earBlack.position.x = sign * 0.02;
    earGroup.add(earBlack);

    return earGroup;
  }
  headGroup.add(createEar(false));
  headGroup.add(createEar(true));

  // Antena asimétrica en la parte superior izquierda de la cabeza (según foto)
  const antennaGroup = new THREE.Group();
  antennaGroup.position.set(0.35, 0.575, -0.05);

  // Base negra corta
  const antBase = new THREE.Mesh(new THREE.BoxGeometry(0.18, 0.12, 0.18), blackMat);
  antBase.position.y = 0.06;
  antennaGroup.add(antBase);

  // Mástil blanco
  const antStem = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.04, 0.3, 16), whiteMat);
  antStem.position.y = 0.25;
  antennaGroup.add(antStem);

  // Cubo superior negro con conector
  const antTip = new THREE.Mesh(new THREE.BoxGeometry(0.16, 0.18, 0.16), blackMat);
  antTip.position.y = 0.46;
  antennaGroup.add(antTip);

  headGroup.add(antennaGroup);

  // Vistas traseras de la cabeza: Válvula / ranura horizontal
  const backVent1 = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.08, 0.04), whiteMat);
  backVent1.position.set(0, 0.12, -0.49);
  headGroup.add(backVent1);

  const backVent2 = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.08, 0.04), whiteMat);
  backVent2.position.set(0, -0.06, -0.49);
  headGroup.add(backVent2);

  // ----------------------------------------------------
  // CUELLO
  // ----------------------------------------------------
  const neckGeo = new THREE.BoxGeometry(0.48, 0.12, 0.4);
  const neck = new THREE.Mesh(neckGeo, blackMat);
  neck.position.y = -0.04;
  robot.add(neck);

  // ----------------------------------------------------
  // TORSO / CUERPO
  // ----------------------------------------------------
  const torsoGroup = new THREE.Group();
  torsoGroup.position.y = -0.52;
  robot.add(torsoGroup);

  // Caja del torso blanca
  const torsoBox = new THREE.Mesh(new THREE.BoxGeometry(0.96, 0.82, 0.62), whiteMat);
  torsoBox.castShadow = true;
  torsoBox.receiveShadow = true;
  torsoGroup.add(torsoBox);

  // Detalles Frontales del Pecho (Fieles a la imagen de referencia):
  // 1. Emblema cuadrado pixelado en el pecho superior derecho
  const badgeFrame = new THREE.Mesh(new THREE.BoxGeometry(0.2, 0.2, 0.04), blackMat);
  badgeFrame.position.set(0.24, 0.18, 0.32);
  torsoGroup.add(badgeFrame);

  // Icono pixelado blanco en el centro del emblema
  const badgeCenter = new THREE.Mesh(new THREE.BoxGeometry(0.09, 0.09, 0.06), whiteMat);
  badgeCenter.position.set(0.24, 0.18, 0.33);
  torsoGroup.add(badgeCenter);

  // 2. Línea y punto negro en el pecho superior izquierdo
  const chestBar = new THREE.Mesh(new THREE.BoxGeometry(0.26, 0.05, 0.03), blackMat);
  chestBar.position.set(-0.16, 0.18, 0.32);
  torsoGroup.add(chestBar);

  const chestDot = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.05, 0.03), blackMat);
  chestDot.position.set(-0.35, 0.18, 0.32);
  torsoGroup.add(chestDot);

  // 3. Panel inferior con rejillas horizontales
  const ventPanel = new THREE.Mesh(new THREE.BoxGeometry(0.55, 0.22, 0.04), blackMat);
  ventPanel.position.set(0, -0.16, 0.32);
  torsoGroup.add(ventPanel);

  const ventSlot1 = new THREE.Mesh(new THREE.BoxGeometry(0.42, 0.035, 0.05), whiteMat);
  ventSlot1.position.set(0, -0.12, 0.33);
  torsoGroup.add(ventSlot1);

  const ventSlot2 = new THREE.Mesh(new THREE.BoxGeometry(0.42, 0.035, 0.05), whiteMat);
  ventSlot2.position.set(0, -0.20, 0.33);
  torsoGroup.add(ventSlot2);

  // 4. Detalle posterior (Mochila / Batería en la espalda según foto trasera)
  const backpack = new THREE.Mesh(new THREE.BoxGeometry(0.55, 0.36, 0.12), blackMat);
  backpack.position.set(0, 0.02, -0.34);
  backpack.castShadow = true;
  torsoGroup.add(backpack);

  const backpackInner = new THREE.Mesh(new THREE.BoxGeometry(0.43, 0.24, 0.14), whiteMat);
  backpackInner.position.set(0, 0.02, -0.34);
  torsoGroup.add(backpackInner);

  // ----------------------------------------------------
  // BRAZOS ARTICULADOS
  // ----------------------------------------------------
  function createArm(isRight) {
    const armGroup = new THREE.Group();
    const sign = isRight ? 1 : -1;
    armGroup.position.set(sign * 0.58, 0.22, 0);

    // Hombro blanco
    const shoulder = new THREE.Mesh(new THREE.BoxGeometry(0.18, 0.2, 0.22), whiteMat);
    shoulder.castShadow = true;
    armGroup.add(shoulder);

    // Rueda / botón negro en el lateral del hombro
    const shoulderPin = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.06, 0.2, 16), blackMat);
    shoulderPin.rotation.z = Math.PI / 2;
    shoulderPin.position.x = sign * 0.08;
    armGroup.add(shoulderPin);

    // Articulación superior negra
    const bicepJoint = new THREE.Mesh(new THREE.BoxGeometry(0.14, 0.08, 0.16), blackMat);
    bicepJoint.position.set(0, -0.14, 0);
    armGroup.add(bicepJoint);

    // Antebrazo blanco
    const forearm = new THREE.Mesh(new THREE.BoxGeometry(0.18, 0.26, 0.2), whiteMat);
    forearm.position.set(0, -0.30, 0);
    forearm.castShadow = true;
    armGroup.add(forearm);

    // Muñeca negra
    const wrist = new THREE.Mesh(new THREE.BoxGeometry(0.14, 0.06, 0.16), blackMat);
    wrist.position.set(0, -0.46, 0);
    armGroup.add(wrist);

    // Mano / Garra negra
    const hand = new THREE.Mesh(new THREE.BoxGeometry(0.16, 0.14, 0.16), blackMat);
    hand.position.set(0, -0.54, 0);
    hand.castShadow = true;
    armGroup.add(hand);

    return armGroup;
  }

  const leftArm = createArm(false);
  const rightArm = createArm(true);
  torsoGroup.add(leftArm);
  torsoGroup.add(rightArm);

  // ----------------------------------------------------
  // PIERNAS Y PIES
  // ----------------------------------------------------
  function createLeg(isRight) {
    const legGroup = new THREE.Group();
    const sign = isRight ? 1 : -1;
    legGroup.position.set(sign * 0.22, -0.45, 0);

    // Articulación superior de la pierna negra
    const hipJoint = new THREE.Mesh(new THREE.BoxGeometry(0.24, 0.12, 0.24), blackMat);
    legGroup.add(hipJoint);

    // Tobillo negro
    const ankle = new THREE.Mesh(new THREE.BoxGeometry(0.24, 0.08, 0.24), blackMat);
    ankle.position.y = -0.12;
    legGroup.add(ankle);

    // Zapato / Pie blanco cúbico
    const foot = new THREE.Mesh(new THREE.BoxGeometry(0.32, 0.22, 0.44), whiteMat);
    foot.position.set(0, -0.26, 0.04);
    foot.castShadow = true;
    legGroup.add(foot);

    // Suela negra del zapato
    const sole = new THREE.Mesh(new THREE.BoxGeometry(0.32, 0.04, 0.44), blackMat);
    sole.position.set(0, -0.38, 0.04);
    legGroup.add(sole);

    return legGroup;
  }

  torsoGroup.add(createLeg(false));
  torsoGroup.add(createLeg(true));

  // ----------------------------------------------------
  // INTERACCIÓN Y ANIMACIÓN
  // ----------------------------------------------------
  let isSpeaking = false;
  let isThinking = false;
  let targetRotation = { x: 0, y: 0 };
  let currentRotation = { x: 0, y: 0 };

  // Seguimiento suave del puntero (mouse o dedo en pantalla)
  function onPointerMove(e) {
    const clientX = e.clientX || (e.touches && e.touches[0].clientX) || 0;
    const clientY = e.clientY || (e.touches && e.touches[0].clientY) || 0;
    const x = (clientX / window.innerWidth) * 2 - 1;
    const y = -(clientY / window.innerHeight) * 2 + 1;
    targetRotation.y = x * 0.55;
    targetRotation.x = -y * 0.35;
  }
  window.addEventListener("mousemove", onPointerMove);
  window.addEventListener("touchmove", onPointerMove, { passive: true });

  // Animación continua a 60-120fps
  const clock = new THREE.Clock();

  function animate() {
    requestAnimationFrame(animate);
    const time = clock.getElapsedTime();

    // Rotación suave con inercia
    currentRotation.x += (targetRotation.x - currentRotation.x) * 0.08;
    currentRotation.y += (targetRotation.y - currentRotation.y) * 0.08;

    headGroup.rotation.y = currentRotation.y;
    headGroup.rotation.x = currentRotation.x;
    torsoGroup.rotation.y = currentRotation.y * 0.3;

    // Flotación / Respiración rítmica sutil
    const bob = Math.sin(time * 2.2) * 0.035;
    robot.position.y = 0.15 + bob;

    // Balanceo suave de brazos
    leftArm.rotation.x = Math.sin(time * 2.2) * 0.08;
    rightArm.rotation.x = -Math.sin(time * 2.2) * 0.08;

    // Parpadeo periódico natural de los ojos pixelados
    const blinkCycle = Math.sin(time * 1.2);
    if (blinkCycle > 0.98) {
      leftEye.scale.y = 0.1;
      rightEye.scale.y = 0.1;
    } else {
      leftEye.scale.y = 1;
      rightEye.scale.y = 1;
    }

    // Estado: Hablando
    if (isSpeaking) {
      const speech = Math.sin(time * 16);
      headGroup.position.y = 0.55 + Math.abs(speech) * 0.04;
      leftEye.material = eyeGlowMat;
      rightEye.material = eyeGlowMat;
      leftEye.scale.y = 0.6 + Math.abs(speech) * 0.6;
      rightEye.scale.y = 0.6 + Math.abs(speech) * 0.6;
    } else if (isThinking) {
      // Estado: Pensando
      headGroup.rotation.z = Math.sin(time * 4) * 0.06;
      const thinkPulse = Math.sin(time * 10);
      badgeCenter.material = thinkPulse > 0 ? blackMat : whiteMat;
      leftEye.material = eyeMat;
      rightEye.material = eyeMat;
    } else {
      headGroup.position.y = 0.55;
      headGroup.rotation.z = 0;
      leftEye.material = eyeMat;
      rightEye.material = eyeMat;
      badgeCenter.material = whiteMat;
    }

    renderer.render(scene, camera);
  }

  animate();

  // Reajuste de pantalla y móvil
  window.addEventListener("resize", () => {
    const isMob = window.innerWidth < 768;
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.position.z = isMob ? 5.8 : 4.6;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
  });

  window.avatar = {
    setSpeaking: (val) => { isSpeaking = val; },
    setThinking: (val) => { isThinking = val; }
  };
})();
