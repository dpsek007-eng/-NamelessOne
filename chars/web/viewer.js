// 서버컴에는 화면이 없다. 만든 것을 보려면 파일을 내려받거나 웹으로 봐야 한다.
// 이쪽이다. python3 -m http.server 만 있으면 돌고, three.js 는 lib/ 에 받아
// 두었으므로 바깥 인터넷도 필요 없다.
//
// 보는 것이 목적이 아니라 "유니티에서 어떻게 보일지"를 미리 보는 것이 목적이다.
// 그래서 실루엣 셰이더를 유니티에 넣을 것과 같은 규칙으로 짰다 —
// 짙은 천 한 색 + 강조색 한 색 + 바닥에서부터 흐려짐.
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const BODIES = [['수호','guard'],['저항','resist'],['헌신','devote'],
                ['탐구','seek'],['도피','flee']];
// 순서는 chars/src/garments.py 의 SLUG 와 같게 둔다 — 위계 순이다.
const CLASSES = [['왕실','royal'],['귀족','noble'],['술사','mage'],['성직','clergy'],
                 ['관리','clerk'],['상인','merchant'],['장인','artisan'],
                 ['병졸','soldier'],['농어민','peasant'],['하인','servant'],
                 ['유랑','vagrant']];

let body = 'guard', cls = 'royal';
let mode = 'one';          // 'one' 한 벌 / 'all' 55벌 격자
const $ = id => document.getElementById(id);

// ---------------------------------------------------------------- 실루엣 재료
// 유니티에 넣을 셰이더와 같은 규칙이다:
//   색은 두 가지뿐 — 천과 강조색. 명암은 아주 얕게만 준다. 형태는 윤곽으로 읽힌다.
//   발끝은 바닥에서 일정 높이까지 알파가 0 으로 떨어진다.
// 높이는 월드가 아니라 제 원점(modelMatrix 의 이동 성분)에서 잰다.
// 블렌더에서 발바닥을 z=0 에 두고 구웠으므로 원점이 곧 발밑이다.
// 월드 Y 를 그냥 쓰면 격자로 늘어놓았을 때 위쪽 줄이 통째로 지워진다.
// 유니티 셰이더도 같은 식이다 (unity_ObjectToWorld._m13).
//
// 스키닝 청크를 직접 넣는 이유: 옷은 SkinnedMesh 라서 뼈 변형을 셰이더가
// 직접 해야 한다. three 는 ShaderMaterial 에도 USE_SKINNING 을 정의해 주고
// bindMatrix·boneTexture 를 알아서 물려 준다.
function silhouette(colour) {
  return new THREE.ShaderMaterial({
    transparent: true, side: THREE.DoubleSide,
    uniforms: {
      uColour:  { value: new THREE.Color(colour) },
      uFadeTop: { value: 0.22 },   // 이 높이(미터)까지 지운다
      uFadeOn:  { value: 1.0 },
    },
    vertexShader: `
      varying float vY; varying vec3 vN;
      #include <common>
      #include <skinning_pars_vertex>
      void main() {
        #include <beginnormal_vertex>
        #include <skinbase_vertex>
        #include <skinnormal_vertex>
        #include <defaultnormal_vertex>
        #include <begin_vertex>
        #include <skinning_vertex>
        vec4 wp = modelMatrix * vec4(transformed, 1.0);
        vY = wp.y - modelMatrix[3][1];
        vN = normalize(transformedNormal);
        gl_Position = projectionMatrix * viewMatrix * wp;
      }`,
    fragmentShader: `
      uniform vec3 uColour; uniform float uFadeTop, uFadeOn;
      varying float vY; varying vec3 vN;
      void main() {
        // 명암은 살짝만. 실루엣이 뭉개지지 않을 만큼.
        float l = 0.80 + 0.20 * clamp(dot(normalize(vN), normalize(vec3(0.3,0.9,0.4))), 0.0, 1.0);
        float a = uFadeOn > 0.5 ? smoothstep(0.0, uFadeTop, vY) : 1.0;
        if (a < 0.01) discard;
        gl_FragColor = vec4(uColour * l, a);
      }`,
  });
}

// ---------------------------------------------------------------- 판 짜기
const view = $('view');
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
view.appendChild(renderer.domElement);

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x17140f);

// 카메라 두 대. 한 벌을 볼 때는 원근으로 가까이, 55벌을 늘어놓을 때는
// 직교로 멀리서 본다 — 격자에서 원근을 쓰면 가장자리 칸이 기울어 보여서
// "옆칸과 실루엣이 다른가"를 볼 수가 없다.
const camOne = new THREE.PerspectiveCamera(35, 1, 0.05, 100);
camOne.position.set(1.3, 1.1, 3.2);
const camAll = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.1, 200);
camAll.position.set(0, 0, 30);

const ctlOne = new OrbitControls(camOne, renderer.domElement);
ctlOne.target.set(0, 0.9, 0);
ctlOne.enableDamping = true;
const ctlAll = new OrbitControls(camAll, renderer.domElement);
ctlAll.enableRotate = false;      // 격자는 정면으로 고정한다
ctlAll.enableDamping = true;
ctlAll.enabled = false;

let camera = camOne, controls = ctlOne;

scene.add(new THREE.HemisphereLight(0xbfd4ff, 0x2a2018, 2.0));
const key = new THREE.DirectionalLight(0xfff2dd, 2.2);
key.position.set(2, 4, 3); scene.add(key);
// 바닥 격자. 발이 바닥에 닿아 있는지 눈으로 보려고 둔다.
const floor = new THREE.GridHelper(8, 32, 0x3a3129, 0x241f1a);
scene.add(floor);

const root = new THREE.Group(); scene.add(root);
const loader = new GLTFLoader();
const cache = new Map();     // url -> Promise<Object3D>
const origMat = new WeakMap();  // mesh -> 원래 머티리얼

// 클론하지 않는다. SkinnedMesh 를 clone() 하면 스켈레톤이 원본 뼈를 가리켜서
// 살이 엉뚱한 데로 끌려간다. 어차피 한 번에 한 벌만 보므로 같은 것을 다시 쓴다.
function load(url) {
  if (!cache.has(url)) {
    cache.set(url, new Promise((res, rej) =>
      loader.load(url,
        g => {
          g.scene.traverse(o => { if (o.isMesh) { origMat.set(o, o.material); o.frustumCulled = false; } });
          res(g.scene);
        },
        undefined,
        e => rej(new Error(url.split('/').pop() + ' — ' + (e.message || '못 읽음')))
      )));
  }
  return cache.get(url);
}

let mats = [];

// 격자 칸 간격. 유니티 IremCharScene.cs 의 StepX/StepY 와 같은 값이다.
const STEP_X = 1.15, STEP_Y = 2.15;

// SkinnedMesh 는 그냥 clone() 하면 안 된다. 복제본의 skeleton 이 원본 뼈를
// 그대로 가리키므로, 칸마다 옮겨 놓아도 살은 전부 원점으로 끌려간다.
// (한 벌만 볼 때는 복제하지 않아서 이 문제가 없었다. 격자에서 처음 걸린다.)
// three 의 SkeletonUtils.clone 이 하는 일을 여기서 한다 — 뼈를 이름으로 다시 맺는다.
function cloneSkinned(src) {
  const dst = src.clone(true);
  const bones = new Map();
  dst.traverse(o => { if (o.isBone) bones.set(o.name, o); });
  const srcMeshes = [];
  src.traverse(o => { if (o.isSkinnedMesh) srcMeshes.push(o); });
  let i = 0;
  dst.traverse(o => {
    if (!o.isSkinnedMesh) return;
    const orig = srcMeshes[i++];
    origMat.set(o, origMat.get(orig));
    o.frustumCulled = false;
    o.bindMatrix.copy(orig.bindMatrix);
    o.bind(new THREE.Skeleton(orig.skeleton.bones.map(b => bones.get(b.name)),
                              orig.skeleton.boneInverses),
           o.bindMatrix);
  });
  return dst;
}

// 칸 이름표. 캔버스에 한글을 그려 스프라이트로 세운다.
// 헤드리스 크롬에도 Noto CJK 가 깔려 있어 그대로 나온다.
function label(text, size = 0.34) {
  const S = 256, c = document.createElement('canvas');
  c.width = S * 2; c.height = S;
  const g = c.getContext('2d');
  g.font = '600 108px "Noto Sans CJK KR", "Noto Sans KR", sans-serif';
  g.fillStyle = '#cdc3b6'; g.textAlign = 'center'; g.textBaseline = 'middle';
  g.fillText(text, S, S / 2 + 6);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: t, transparent: true }));
  sp.scale.set(size * 2, size, 1);
  return sp;
}

function dress(obj, which) {
  obj.traverse(o => {
    if (!o.isMesh) return;
    const orig = origMat.get(o);
    // 강조색 서브메시는 머티리얼 이름으로 가른다 — 내보낼 때 accent 로 이름 붙였다.
    const isAccent = /accent/i.test(orig?.name || '');
    if ($('silhouette').checked) {
      const c = isAccent ? $('accent').value : (which === 'body' ? '#0d0b0a' : '#221b16');
      const m = silhouette(c);
      m.uniforms.uFadeTop.value = parseFloat($('fadeH').value);
      m.uniforms.uFadeOn.value = $('fade').checked ? 1 : 0;
      o.material = m; mats.push(m);
    } else {
      o.material = orig;
      if (isAccent) { o.material = orig.clone(); o.material.color.set($('accent').value); }
    }
  });
}

async function show() {
  root.clear(); root.rotation.set(0, 0, 0); mats = [];
  floor.visible = (mode === 'one');
  camera   = mode === 'one' ? camOne : camAll;
  controls = mode === 'one' ? ctlOne : ctlAll;
  ctlOne.enabled = (mode === 'one');
  ctlAll.enabled = (mode === 'all');
  resize();
  try {
    if (mode === 'one') await showOne(); else await showAll();
    $('err').style.display = 'none';
  } catch (e) {
    $('err').style.display = 'block';
    $('err').textContent = '못 읽었다: ' + e.message;
  }
}

async function showOne() {
  const meas = [];
  const jobs = [];
  if ($('showBody').checked)    jobs.push(['body',    `../out/bodies/${body}.glb`]);
  if ($('showGarment').checked) jobs.push(['garment', `../out/garments/${body}_${cls}.glb`]);
  for (const [which, url] of jobs) {
    const g = await load(url);
    dress(g, which);
    root.add(g);
    g.updateMatrixWorld(true);
    const b = new THREE.Box3().setFromObject(g);
    meas.push(`${which === 'body' ? '몸' : '옷'} · 높이 ${(b.max.y - b.min.y).toFixed(3)}m`
            + ` · 폭 ${(b.max.x - b.min.x).toFixed(3)}m`
            + ` · 밑단 ${b.min.y.toFixed(3)}m`);
    if ($('showBones').checked) {
      const h = new THREE.SkeletonHelper(g);
      h.material.depthTest = false; root.add(h);
    }
  }
  $('meas').innerHTML = meas.join('<br>') || '—';
}

// 55벌을 한 화면에. 유니티 [이렘/캐릭터 확인 신] 과 같은 배치다 —
// 가로 11칸이 계층, 세로 5줄이 체형. 옆칸과 다르지 않은 칸이 있으면 그 칸은 실패다.
async function showAll() {
  $('meas').textContent = '55벌 읽는 중…';
  const topY = STEP_Y * (BODIES.length - 1);

  for (let c = 0; c < CLASSES.length; c++) {
    const t = label(CLASSES[c][0]);
    t.position.set(c * STEP_X, topY + 2.15, 0);
    root.add(t);
  }
  for (let r = 0; r < BODIES.length; r++) {
    const t = label(BODIES[r][0]);
    t.position.set(-1.1, (BODIES.length - 1 - r) * STEP_Y + 0.9, 0);
    root.add(t);
  }

  let n = 0;
  for (let r = 0; r < BODIES.length; r++) {
    const bslug = BODIES[r][1];
    const src = $('showBody').checked ? await load(`../out/bodies/${bslug}.glb`) : null;
    for (let c = 0; c < CLASSES.length; c++) {
      const cell = new THREE.Group();
      cell.position.set(c * STEP_X, (BODIES.length - 1 - r) * STEP_Y, 0);
      root.add(cell);
      if (src) { const b = cloneSkinned(src); dress(b, 'body'); cell.add(b); }
      if ($('showGarment').checked) {
        // 옷은 55벌이 전부 다른 파일이라 한 번씩만 쓴다 — 복제할 일이 없다.
        const g = await load(`../out/garments/${bslug}_${CLASSES[c][1]}.glb`);
        dress(g, 'garment'); cell.add(g);
      }
      n++;
      $('meas').textContent = `${n}/55`;
    }
  }

  // 격자가 다 들어오게 직교 카메라를 맞춘다.
  const w = STEP_X * (CLASSES.length - 1) + 2.4;
  const h = topY + 4.3;
  camAll.position.set(w * 0.5 - 1.2, h * 0.5 - 0.6, 30);
  ctlAll.target.set(camAll.position.x, camAll.position.y, 0);
  fitAll(w, h);
  $('meas').textContent = `${n}벌 · 가로 계층 11 · 세로 체형 5`;
}

let allW = 14, allH = 13;
function fitAll(w, h) {
  allW = w; allH = h;
  const a = view.clientWidth / Math.max(1, view.clientHeight);
  const half = Math.max(h * 0.5, w * 0.5 / a);
  camAll.top = half; camAll.bottom = -half;
  camAll.left = -half * a; camAll.right = half * a;
  camAll.updateProjectionMatrix();
}

// ---------------------------------------------------------------- 단추
function buttons(host, list, get, set) {
  const paint = () => [...host.children].forEach(
    b => b.classList.toggle('on', b.dataset.slug === get()));
  for (const [ko, slug] of list) {
    const b = document.createElement('button');
    b.textContent = ko; b.dataset.slug = slug;
    b.onclick = () => { set(slug); paint(); show(); };
    host.appendChild(b);
  }
  paint();
}
buttons($('bodies'),  BODIES,  () => body, v => body = v);
buttons($('classes'), CLASSES, () => cls,  v => cls  = v);

for (const id of ['showBody', 'showGarment', 'showBones', 'silhouette', 'fade'])
  $(id).onchange = show;
$('all').onclick = () => {
  mode = mode === 'one' ? 'all' : 'one';
  $('all').textContent = mode === 'one' ? '55벌 한눈에' : '한 벌만 보기';
  $('all').classList.toggle('on', mode === 'all');
  show();
};
$('accent').oninput = show;
$('fadeH').oninput = () => {
  const v = parseFloat($('fadeH').value);
  mats.forEach(m => m.uniforms.uFadeTop.value = v);
};

// 주소 끝에 #all 을 붙이면 격자로 연다. 헤드리스 크롬으로 찍을 때 쓴다 —
// 단추를 누를 방법이 없기 때문이다.
if (location.hash === '#all') {
  mode = 'all';
  $('all').textContent = '한 벌만 보기';
  $('all').classList.add('on');
}

// ---------------------------------------------------------------- 돌리기
function resize() {
  const w = view.clientWidth, h = view.clientHeight;
  renderer.setSize(w, h, false);
  camOne.aspect = w / h; camOne.updateProjectionMatrix();
  fitAll(allW, allH);
}
addEventListener('resize', resize); resize();

renderer.setAnimationLoop(() => {
  if (mode === 'one' && $('spin').checked) root.rotation.y += 0.006;
  controls.update();
  renderer.render(scene, camera);
});

show();
