// ==========================================
// 1. ข้อมูลเริ่มต้น (State)
// ==========================================
const menuData = [
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
const PROMPTPAY_ID = "0812345678"; 

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

  const newItems = Object.keys(currentCart).map(menuId => {
    const item = menuData.find(m => m.id == menuId);
    return {
      menuId: item.id,
      name: item.name,
      price: item.price,
      quantity: currentCart[menuId]
    };
  });

  const payload = {
    tableNo: tableNo,
    items: newItems,
    roundTotal: total
  };

  try {
    // ส่งข้อมูลไปยัง Backend API
    const response = await fetch('http://localhost:3000/api/orders', {
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
      alert(`เกิดข้อผิดพลาด: ${result.message}`);
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
    const response = await fetch(`http://localhost:3000/api/orders/table/${tableNo}`);
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
        <span class="font-medium">${item.name}</span>
        <div class="space-x-8">
          <span class="text-slate-500">x${item.quantity}</span>
          <span class="font-semibold">${subtotal.toFixed(2)}</span>
        </div>
      `;
      billContainer.appendChild(row);
    });

    document.getElementById('bill-total-price').innerText = grandTotal.toFixed(2);
    document.getElementById('qr-code-img').src = `https://promptpay.io/${PROMPTPAY_ID}/${grandTotal.toFixed(2)}.png`;

    document.getElementById('page-menu').classList.add('hidden');
    document.getElementById('page-bill').classList.remove('hidden');
    window.scrollTo(0, 0);

  } catch (error) {
    console.error("Error fetching bill:", error);
    alert("ไม่สามารถดึงข้อมูลบิลได้");
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
document.addEventListener('DOMContentLoaded', () => {
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
    const response = await fetch('http://localhost:3000/api/orders/checkout', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tableNo: tableNo })
    });

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