import {expect,test} from "./base";
import {PIPELINE_RECOMMEND} from "./fixtures/pipeline";

test("focus actions show the correct station, reopen, and never allocate again",async({page})=>{
 let recommendations=0;
 await page.route("**/api/recommend",route=>{recommendations++;return route.fulfill({json:PIPELINE_RECOMMEND});});
 const directory=await (await page.request.get("/api/stations")).json();
 const nameFor=(id:string)=>directory.stations.find((s:{station_id:string;name:string})=>s.station_id===id).name;
 await page.goto("/driver");
 await page.getByRole("button",{name:"Tìm kế hoạch sạc",exact:true}).click();
 await expect(page.getByTestId("plan-hero")).toBeVisible();
 await expect(page.getByTestId("station-map-info")).toHaveCount(0);
 await page.getByRole("button",{name:"Định vị trạm chính",exact:true}).click();
 await expect(page.getByTestId("station-map-info")).toContainText(nameFor(PIPELINE_RECOMMEND.primary.station_id));
 await expect(page.getByTestId("station-map-info")).toContainText("85%");
 await page.getByRole("button",{name:"Định vị trạm dự phòng",exact:true}).click();
 await expect(page.getByTestId("station-map-info")).toContainText(nameFor(PIPELINE_RECOMMEND.backup.station_id));
 await expect(page.getByTestId("station-map-info")).toContainText("60%");
 await page.getByRole("button",{name:"Đóng thông tin trạm",exact:true}).click();
 await expect(page.getByTestId("station-map-info")).toHaveCount(0);
 await page.getByRole("button",{name:"Định vị trạm dự phòng",exact:true}).click();
 await expect(page.getByTestId("station-map-info")).toBeVisible();
 expect(recommendations).toBe(1);
 await page.getByLabel("Điểm đi",{exact:true}).fill("Địa chỉ chưa chọn");
 await expect(page.getByTestId("station-map-info")).toHaveCount(0);
});
