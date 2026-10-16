// ==========================================
// 1. ข้อมูลเริ่มต้น (State)
// ==========================================
// ค่าเริ่มต้น (สำรอง) ราคาจริงโหลดจากเซิร์ฟเวอร์ที่ /api/menu และเซิร์ฟเวอร์คิดราคาเองเสมอ
let menuData = [
  { id: 1, name: "ข้าวมันไก่กุ๊กๆ", price: 50, category: "จานเดียว", img: "🍗" },
  { id: 2, name: "ข้าวผัดกระเพราหมูกรอบ", price: 65, category: "จานเดียว", img: "🍳" },
  { id: 3, name: "ก๋วยเตี๋ยวต้มยำกุ้ง", price: 80, category: "ต้ม/แกง", img: "🍜" },
  { id: 4, name: "ต้มยำกุ้งน้ำข้น", price: 150, category: "ต้ม/แกง", img: "🥘" },
  { id: 5, name: "ชาไทยเย็น", price: 35, category: "เครื่องดื่ม", img: "🧋" }
];

// เปลี่ยนจาก cart = {} เป็นการเก็บแยกตามหมายเลขโต๊ะ เช่น { "01": { 1: 2 }, "02": { 3: 1 } }
let cartsByTable = {};

// เก็บประวัติออเดอร์สะสมทุกรอบของแต่ละโต๊ะที่ส่งเข้า API แล้ว
let ordersHistoryByTable = {}; 

let currentCategory = 'all';

// Backend อยู่ origin เดียวกับหน้าเว็บ (FastAPI เสิร์ฟทั้งคู่) จึงไม่ต้องใช้ CORS / พอร์ตแยก
const API_BASE = '';

// ป้องกัน XSS: ชื่อเมนูที่มาจากเซิร์ฟเวอร์ต้อง escape ก่อนใส่ innerHTML
function escapeHtml(text) {
  return String(text).replace(/[&<>"']/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[c]));
}

// อ่านข้อความ error จาก API (FastAPI ใช้ detail, 422 เป็น list)
function apiErrorMessage(result, status) {
  if (status === 429) return 'ส่งคำขอถี่เกินไป กรุณารอสักครู่แล้วลองใหม่';
  if (status === 401) return 'รหัสพนักงาน (API key) ไม่ถูกต้อง';
  const d = result && (result.detail || result.message);
  if (Array.isArray(d)) return d.map(e => e.msg).join(', ');
  return d || 'เกิดข้อผิดพลาดไม่ทราบสาเหตุ';
}

// โหลดเมนูและราคาจริงจากเซิร์ฟเวอร์ ถ้าโหลดไม่ได้จะใช้ค่าสำรองด้านบน
async function loadMenu() {
  try {
    const response = await fetch(`${API_BASE}/api/menu`);
    if (!response.ok) return;
    const data = await response.json();
    if (Array.isArray(data) && data.length > 0) {
      menuData = data.map(m => ({ ...m, price: Number(m.price) }));
    }
  } catch (error) {
    console.warn("Load menu failed, use the default menu:", error);
  }
}

// ดึงหมายเลขโต๊ะที่เลือกอยู่ปัจจุบัน
function getCurrentTableNo() {
  return document.getElementById('table-select').value;
}

// ดึงข้อมูลตะกร้าสินค้าของโต๊ะปัจจุบัน
function getCurrentCart() {
  const tableNo = getCurrentTableNo();
  if (!cartsByTable[tableNo]) {
    cartsByTable[tableNo] = {};
  }
  return cartsByTable[tableNo];
}

// ==========================================
// 2. ฟังก์ชันการทำงานหลัก (Functions)
// ==========================================

// แสดงรายการเมนูตามหมวดหมู่ และแสดงจำนวนที่สั่งของโต๊ะปัจจุบัน
function renderMenu() {
  const menuContainer = document.getElementById('menu-list');
  menuContainer.innerHTML = '';

  const currentCart = getCurrentCart();
  const filteredData = currentCategory === 'all' 
    ? menuData 
    : menuData.filter(item => item.category === currentCategory);

  filteredData.forEach(item => {
    const qty = currentCart[item.id] || 0;
    const itemEl = document.createElement('div');
    itemEl.className = "bg-white p-3.5 rounded-xl shadow-sm border border-slate-200 flex justify-between items-center";
    itemEl.innerHTML = `
      <div class="flex items-center gap-3">
        <span class="text-2xl bg-slate-100 p-2 rounded-lg">${item.img}</span>
        <div>
          <h3 class="text-sm font-medium text-slate-800">${item.name}</h3>
          <p class="text-xs font-semibold text-slate-600">${item.price.toFixed(2)} บาท</p>
        </div>
      </div>
      <div class="flex items-center gap-1 bg-slate-50 border border-slate-200 rounded-lg p-0.5">
        <button onclick="updateQty(${item.id}, -1)" class="w-7 h-7 rounded bg-white text-slate-700 font-bold hover:bg-slate-100 shadow-sm transition text-xs">-</button>
        <span class="w-6 text-center text-xs font-semibold">${qty}</span>
        <button onclick="updateQty(${item.id}, 1)" class="w-7 h-7 rounded bg-slate-900 text-white font-bold hover:bg-slate-800 shadow-sm transition text-xs">+</button>
      </div>
    `;
    menuContainer.appendChild(itemEl);
  });

  calculateTotal();
}

// อัปเดตจำนวนสินค้าในตะกร้าเฉพาะของโต๊ะปัจจุบัน
function updateQty(id, change) {
  const tableNo = getCurrentTableNo();
  const currentCart = getCurrentCart();
  
  const currentQty = currentCart[id] || 0;
  const newQty = currentQty + change;

  if (newQty <= 0) {
    delete currentCart[id];
  } else {
    currentCart[id] = newQty;
  }

  renderMenu();
}

// คำนวณราคารวมในตะกร้าเฉพาะของโต๊ะปัจจุบัน
function calculateTotal() {
  let total = 0;
  const currentCart = getCurrentCart();

  menuData.forEach(item => {
    if (currentCart[item.id]) {
      total += item.price * currentCart[item.id];
    }
  });

  document.getElementById('cart-total').innerText = total.toFixed(2);
  return total;
}

// ส่งออเดอร์ของโต๊ะปัจจุบันไปยัง API
async function submitOrderToAPI() {
  const tableNo = getCurrentTableNo();
  const currentCart = getCurrentCart();
  const total = calculateTotal();

  if (total === 0) {
    alert(`โต๊ะ ${tableNo}: กรุณาเลือกรายการอาหารอย่างน้อย 1 รายการเพื่อสั่งซื้อ`);
    return;
  }

  // ส่งเฉพาะ menuId + จำนวน เซิร์ฟเวอร์จะหาชื่อ/ราคาจากตารางเมนูเอง (ไม่เชื่อราคาจากหน้าเว็บ)
  const newItems = Object.keys(currentCart).map(menuId => ({
    menuId: Number(menuId),
    quantity: currentCart[menuId]
  }));

  const payload = {
    tableNo: tableNo,
    items: newItems
  };

  try {
    // ส่งข้อมูลไปยัง Backend API
    const response = await fetch(`${API_BASE}/api/orders`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    });

    const result = await response.json();

    if (response.ok) {
      alert(`ส่งรายการสั่งซื้อรอบใหม่สำหรับ "โต๊ะ ${tableNo}" เรียบร้อยแล้ว!`);
      // ล้างตะกร้าเฉพาะของโต๊ะปัจจุบันเมื่อส่งสำเร็จ
      cartsByTable[tableNo] = {}; 
      renderMenu();
    } else {
      alert(`เกิดข้อผิดพลาด: ${apiErrorMessage(result, response.status)}`);
    }
  } catch (error) {
    console.error("Error submitting order:", error);
    alert("ไม่สามารถเชื่อมต่อกับเซิร์ฟเวอร์ได้");
  }
}

// ดึงรายการอาหารสะสมทั้งหมดของโต๊ะปัจจุบันมาแสดงบิล
async function fetchAndShowBill() {
  const tableNo = getCurrentTableNo();

  try {
    // ดึงประวัติรายการอาหารจาก Backend API เฉพาะของโต๊ะนี้
    const response = await fetch(`${API_BASE}/api/orders/table/${encodeURIComponent(tableNo)}`);
    if (!response.ok) {
      alert(`ไม่สามารถดึงข้อมูลบิลได้: ${apiErrorMessage(await response.json().catch(() => ({})), response.status)}`);
      return;
    }
    const historyItems = await response.json();

    if (!historyItems || historyItems.length === 0) {
      alert(`โต๊ะ ${tableNo} ยังไม่มีรายการอาหารที่สั่งครับ`);
      return;
    }

    // รวมรายการอาหารที่ซ้ำกัน
    const aggregatedItems = aggregateItems(historyItems);
    const grandTotal = aggregatedItems.reduce((sum, item) => sum + (item.price * item.quantity), 0);

    // แสดงผลข้อมูลบิลบน UI
    document.getElementById('bill-table-no').innerText = tableNo;
    document.getElementById('bill-date').innerText = `อัปเดตล่าสุด: ${new Date().toLocaleTimeString('th-TH')}`;
    
    const billContainer = document.getElementById('bill-items');
    billContainer.innerHTML = '';

    aggregatedItems.forEach(item => {
      const subtotal = item.price * item.quantity;
      const row = document.createElement('div');
      row.className = "flex justify-between items-center border-b border-slate-100 pb-1.5";
      row.innerHTML = `
        <span class="font-medium">${escapeHtml(item.name)}</span>
        <div class="space-x-8">
          <span class="text-slate-500">x${item.quantity}</span>
          <span class="font-semibold">${subtotal.toFixed(2)}</span>
        </div>
      `;
      billContainer.appendChild(row);
    });

    document.getElementById('bill-total-price').innerText = grandTotal.toFixed(2);
    await renderPaymentQr(tableNo);

    document.getElementById('page-menu').classList.add('hidden');
    document.getElementById('page-bill').classList.remove('hidden');
    window.scrollTo(0, 0);

  } catch (error) {
    console.error("Error fetching bill:", error);
    alert("ไม่สามารถดึงข้อมูลบิลได้");
  }
}

// ขอข้อความ PromptPay (พร้อมยอดเงินของโต๊ะ) จากเซิร์ฟเวอร์ แล้ววาดเป็น QR
// เลขบัญชีอยู่ฝั่งเซิร์ฟเวอร์ (.env) ไม่ฝังในโค้ดหน้าเว็บ
async function renderPaymentQr(tableNo) {
  const box = document.getElementById('qr-code-box');
  box.innerHTML = '';
  try {
    const response = await fetch(`${API_BASE}/api/orders/table/${encodeURIComponent(tableNo)}/qr`);
    if (!response.ok) throw new Error(`QR request failed: ${response.status}`);
    const { payload } = await response.json();
    new QRCode(box, { text: payload, width: 176, height: 176, correctLevel: QRCode.CorrectLevel.M });
  } catch (error) {
    console.error("Error rendering QR:", error);
    box.textContent = 'สร้าง QR ไม่สำเร็จ';
  }
}

// รวมรายการอาหารที่ซ้ำกัน
function aggregateItems(items) {
  const result = {};
  items.forEach(item => {
    if (result[item.menuId]) {
      result[item.menuId].quantity += item.quantity;
      result[item.menuId].subtotal += item.price * item.quantity;
    } else {
      result[item.menuId] = {
        ...item,
        subtotal: item.price * item.quantity
      };
    }
  });
  return Object.values(result);
}

function filterCategory(cat, btnElement) {
  currentCategory = cat;
  document.querySelectorAll('.cat-btn').forEach(btn => {
    btn.classList.remove('bg-slate-900', 'text-white');
    btn.classList.add('bg-slate-100', 'text-slate-600');
  });
  btnElement.classList.remove('bg-slate-100', 'text-slate-600');
  btnElement.classList.add('bg-slate-900', 'text-white');
  renderMenu();
}

// ==========================================
// 3. ผูก Event Listeners (DOM Event Binding)
// ==========================================
document.addEventListener('DOMContentLoaded', async () => {
  await loadMenu();
  renderMenu();

  // ปุ่มเปลี่ยนหมวดหมู่
  document.getElementById('btn-cat-all').addEventListener('click', (e) => filterCategory('all', e.target));
  document.getElementById('btn-cat-single').addEventListener('click', (e) => filterCategory('จานเดียว', e.target));
  document.getElementById('btn-cat-soup').addEventListener('click', (e) => filterCategory('ต้ม/แกง', e.target));
  document.getElementById('btn-cat-drink').addEventListener('click', (e) => filterCategory('เครื่องดื่ม', e.target));

  // ปุ่มแอ็กชันต่างๆ
  document.getElementById('btn-submit-order').addEventListener('click', submitOrderToAPI);
  document.getElementById('btn-view-bill').addEventListener('click', fetchAndShowBill);
  document.getElementById('btn-back-to-menu').addEventListener('click', () => {
    document.getElementById('page-bill').classList.add('hidden');
    document.getElementById('page-menu').classList.remove('hidden');
  });

  // เช็กบิล / ล้างข้อมูลของโต๊ะนั้นเมื่อชำระเงินเสร็จ
  document.getElementById('btn-confirm-payment').addEventListener('click', async () => {
  const tableNo = getCurrentTableNo();
  
  try {
    // ส่งสัญญาณไปบอก Backend Server ให้เปลี่ยนสถานะโต๊ะนี้เป็นชำระเงินแล้ว (Paid)
    // การปิดบิลต้องใช้รหัสพนักงาน (API key) ถามตอนกดปุ่ม ไม่ฝังไว้ในโค้ดและไม่เก็บลงเครื่อง
    const staffKey = window.prompt('สำหรับพนักงาน: กรอกรหัสพนักงาน (API key) เพื่อยืนยันชำระเงิน');
    if (!staffKey) return;

    const response = await fetch(`${API_BASE}/api/orders/checkout`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-API-Key': staffKey },
      body: JSON.stringify({ tableNo: tableNo })
    });

    if (!response.ok) {
      const result = await response.json().catch(() => ({}));
      alert(`ปิดบิลไม่สำเร็จ: ${apiErrorMessage(result, response.status)}`);
      return;
    }

    if (response.ok) {
      alert(`โต๊ะ ${tableNo}: ชำระเงินเรียบร้อยแล้ว ปิดบิลสำเร็จ!`);

      // ล้างเฉพาะตะกร้าเลือกอาหารชั่วคราวบนหน้าเว็บ
      delete cartsByTable[tableNo];

      document.getElementById('page-bill').classList.add('hidden');
      document.getElementById('page-menu').classList.remove('hidden');
      renderMenu();
    }
  } catch (error) {
    console.error("Checkout error:", error);
    alert("ไม่สามารถดำเนินการเช็กบิลได้");
  }
});

  // เมื่อสลับโต๊ะ ให้ Render หน้าจอใหม่ตามข้อมูลของโต๊ะนั้นทันที
  document.getElementById('table-select').addEventListener('change', () => {
    renderMenu();
  });
});