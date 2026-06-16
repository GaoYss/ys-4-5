<template>
  <div class="split-layout">
    <section class="panel form-panel">
      <h2>新增楼栋</h2>
      <form @submit.prevent="saveBuilding" class="form-grid">
        <label>楼栋名称<input v-model="buildingForm.name" required placeholder="1号楼" /></label>
        <label>地址<input v-model="buildingForm.address" placeholder="小区东区" /></label>
        <label>楼层数<input v-model.number="buildingForm.floor_count" type="number" min="1" /></label>
        <label>单元数<input v-model.number="buildingForm.unit_count" type="number" min="1" /></label>
        <label>楼管员<input v-model="buildingForm.manager" /></label>
        <button type="submit">保存楼栋</button>
      </form>

      <h2>新增房屋</h2>
      <form @submit.prevent="saveRoom" class="form-grid">
        <label>所属楼栋
          <select v-model="roomForm.building" required>
            <option value="" disabled>请选择</option>
            <option v-for="building in allBuildings" :key="building.id" :value="building.id">{{ building.name }}</option>
          </select>
        </label>
        <label>房号<input v-model="roomForm.room_no" required placeholder="1-101" /></label>
        <label>业主<input v-model="roomForm.owner_name" required /></label>
        <label>电话<input v-model="roomForm.phone" /></label>
        <label>面积<input v-model.number="roomForm.area" type="number" step="0.01" min="0" /></label>
        <button type="submit">保存房屋</button>
      </form>
    </section>

    <section class="panel">
      <div class="panel-head">
        <h2>楼栋列表</h2>
        <div class="filter-bar">
          <div class="filter-group">
            <span class="filter-label">欠费筛选：</span>
            <button
              v-for="opt in debtFilterOptions"
              :key="opt.value"
              :class="{ active: debtFilter === opt.value }"
              @click="setDebtFilter(opt.value)"
            >
              {{ opt.label }}
            </button>
          </div>
          <div class="filter-group">
            <span class="filter-label">高欠费阈值(元)：</span>
            <input
              type="number"
              class="threshold-input"
              v-model.number="highDebtThreshold"
              min="0"
              step="100"
              @change="load"
              @keyup.enter="load"
            />
          </div>
          <button @click="load">刷新</button>
        </div>
      </div>
      <DataTable :columns="buildingColumns" :rows="buildings">
        <template #cell-display_amount="{ row }">
          <span v-if="debtFilter === 'overdue'" class="amount overdue">¥{{ formatAmount(row.total_overdue_amount) }}</span>
          <span v-else class="amount unpaid">¥{{ formatAmount(row.total_unpaid_amount) }}</span>
        </template>
      </DataTable>

      <div class="panel-head section-gap">
        <h2>房屋档案</h2>
      </div>
      <DataTable :columns="roomColumns" :rows="rooms">
        <template #cell-unpaid_amount="{ row }">
          <span v-if="row.unpaid_amount > 0" class="amount unpaid">¥{{ formatAmount(row.unpaid_amount) }}</span>
          <span v-else class="amount">-</span>
        </template>
        <template #cell-overdue_amount="{ row }">
          <span v-if="row.overdue_amount > 0" class="amount overdue">¥{{ formatAmount(row.overdue_amount) }}</span>
          <span v-else class="amount">-</span>
        </template>
      </DataTable>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { propertyApi } from "../api/property";
import DataTable from "../components/DataTable.vue";

const buildings = ref([]);
const allBuildings = ref([]);
const rooms = ref([]);
const debtFilter = ref("");
const highDebtThreshold = ref(500);
const buildingForm = reactive({ name: "", address: "", floor_count: 1, unit_count: 1, manager: "" });
const roomForm = reactive({ building: "", room_no: "", owner_name: "", phone: "", area: 0 });

const debtFilterOptions = [
  { value: "", label: "全部" },
  { value: "unpaid", label: "欠费" },
  { value: "overdue", label: "逾期" },
  { value: "high_debt", label: "高欠费" }
];

const buildingColumns = computed(() => [
  { key: "name", label: "楼栋" },
  { key: "address", label: "地址" },
  { key: "manager", label: "楼管员" },
  { key: "room_count", label: "房屋数" },
  { key: "unpaid_room_count", label: "欠费户数" },
  { key: "overdue_room_count", label: "逾期户数" },
  { key: "high_debt_room_count", label: `高欠费户(≥${highDebtThreshold.value}元)` },
  { key: "display_amount", label: debtFilter.value === "overdue" ? "逾期总额" : "欠费总额" }
]);

const roomColumns = [
  { key: "building_name", label: "楼栋" },
  { key: "room_no", label: "房号" },
  { key: "owner_name", label: "业主" },
  { key: "phone", label: "电话" },
  { key: "area", label: "面积" },
  { key: "unpaid_amount", label: "欠费金额" },
  { key: "overdue_amount", label: "逾期金额" }
];

function formatAmount(val) {
  if (val === null || val === undefined) return "0.00";
  return Number(val).toFixed(2);
}

function setDebtFilter(value) {
  debtFilter.value = value;
  load();
}

async function load() {
  const params = {};
  if (debtFilter.value) {
    params.debt_status = debtFilter.value;
  }
  if (highDebtThreshold.value !== null && highDebtThreshold.value !== undefined && highDebtThreshold.value >= 0) {
    params.high_debt_threshold = highDebtThreshold.value;
  }
  const [buildingData, roomData] = await Promise.all([
    propertyApi.listBuildings(params),
    propertyApi.listRooms(params)
  ]);
  buildings.value = buildingData;
  rooms.value = roomData;
  if (!debtFilter.value) {
    allBuildings.value = buildingData;
  }
}

async function saveBuilding() {
  await propertyApi.createBuilding({ ...buildingForm });
  Object.assign(buildingForm, { name: "", address: "", floor_count: 1, unit_count: 1, manager: "" });
  await load();
}

async function saveRoom() {
  await propertyApi.createRoom({ ...roomForm });
  Object.assign(roomForm, { building: "", room_no: "", owner_name: "", phone: "", area: 0 });
  await load();
}

onMounted(load);
</script>

<style scoped>
.filter-bar {
  display: flex;
  align-items: center;
  gap: 12px;
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 6px;
}

.filter-label {
  font-size: 13px;
  color: #666;
}

.filter-group button {
  padding: 4px 12px;
  font-size: 13px;
  border: 1px solid #d9d9d9;
  background: #fff;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
}

.filter-group button:hover {
  border-color: #1890ff;
  color: #1890ff;
}

.filter-group button.active {
  background: #1890ff;
  border-color: #1890ff;
  color: #fff;
}

.amount {
  font-weight: 500;
}

.amount.unpaid {
  color: #fa8c16;
}

.amount.overdue {
  color: #f5222d;
}

.threshold-input {
  width: 100px;
  padding: 4px 8px;
  font-size: 13px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  outline: none;
  transition: border-color 0.2s;
}

.threshold-input:focus {
  border-color: #1890ff;
}
</style>
