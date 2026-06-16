import { http, unwrap } from "./http";

export const propertyApi = {
  dashboard: () => http.get("/dashboard/").then(unwrap),
  listBuildings: (params = {}) => http.get("/buildings/", { params }).then(unwrap),
  createBuilding: (payload) => http.post("/buildings/", payload).then(unwrap),
  listRooms: (params = {}) => http.get("/rooms/", { params }).then(unwrap),
  createRoom: (payload) => http.post("/rooms/", payload).then(unwrap),
  listFeeTypes: () => http.get("/fee-types/").then(unwrap),
  createFeeType: (payload) => http.post("/fee-types/", payload).then(unwrap),
  listBills: (params = {}) => http.get("/bills/", { params }).then(unwrap),
  generateBills: (payload) => http.post("/bills/generate/", payload).then(unwrap),
  payBill: (id, payload) => http.post(`/bills/${id}/pay/`, payload).then(unwrap),
  listPayments: () => http.get("/payments/").then(unwrap),
  listReminders: () => http.get("/reminders/").then(unwrap),
  createOverdueReminders: (payload) => http.post("/reminders/create_overdue/", payload).then(unwrap)
};
