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
              :class="{ active: debtFilter === opt.value, disabled: loading }"
              :disabled="loading"
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
              :class="{ 'input-error': thresholdError }"
              v-model="thresholdInput"
              min="0"
              step="100"
              :disabled="loading"
              @change="handleThresholdChange"
              @keyup.enter="handleThresholdChange"
            />
            <button @click="load" :disabled="loading">刷新</button>
          </div>
        </div>
        <div v-if="thresholdError" class="error-tip">{{ thresholdError }}</div>
      </div>

      <div v-if="loading" class="loading-wrap">
        <div class="loading-spinner"></div>
        <span class="loading-text">加载中...</span>
      </div>

      <template v-else>
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
      </template>
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
const thresholdInput = ref("500");
const loading = ref(false);
const thresholdError = ref("");
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

function validateThreshold() {
  const val = thresholdInput.value.trim();
  if (val === "" || val === null || val === undefined) {
    thresholdError.value = "请输入高欠费阈值";
    return false;
  }
  const num = Number(val);
  if (isNaN(num)) {
    thresholdError.value = "请输入有效的数字";
    return false;
  }
  if (num < 0) {
    thresholdError.value = "阈值不能为负数";
    return false;
  }
  thresholdError.value = "";
  highDebtThreshold.value = num;
  return true;
}

function handleThresholdChange() {
  if (!validateThreshold()) return;
  load();
}

function setDebtFilter(value) {
  if (loading.value) return;
  debtFilter.value = value;
  load();
}

async function load() {
  if (!validateThreshold()) return;
  loading.value = true;
  buildings.value = [];
  rooms.value = [];
  try {
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
  } finally {
    loading.value = false;
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
  flex-wrap: wrap;
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

.filter-group button:hover:not(:disabled) {
  border-color: #1890ff;
  color: #1890ff;
}

.filter-group button.active {
  background: #1890ff;
  border-color: #1890ff;
  color: #fff;
}

.filter-group button:disabled {
  cursor: not-allowed;
  opacity: 0.6;
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

.threshold-input:disabled {
  background: #f5f5f5;
  cursor: not-allowed;
}

.threshold-input.input-error {
  border-color: #f5222d;
}

.error-tip {
  margin-top: 8px;
  font-size: 12px;
  color: #f5222d;
}

.loading-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 60px 0;
  color: #999;
  font-size: 14px;
}

.loading-spinner {
  width: 20px;
  height: 20px;
  border: 2px solid #e0e0e0;
  border-top-color: #1890ff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin-right: 8px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-text {
  font-size: 13px;
}

.section-gap {
  margin-top: 24px;
}
</style>
