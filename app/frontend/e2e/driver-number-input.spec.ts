import { expect, test } from "./base";

test("driver numeric fields keep empty draft and accept comma/dot decimals", async ({
  page,
}) => {
  await page.goto("/driver");

  await page
    .locator("details.driver-advanced")
    .evaluate((el) => {
      (el as HTMLDetailsElement).open = true;
    });

  const soc = page.getByLabel("SOC %");
  const battery = page.getByLabel("Battery kWh");
  const consumption = page.getByLabel("Consumption kWh/km");
  const submit = page.getByRole("button", { name: /Tìm kế hoạch sạc/i });

  await soc.fill("");
  await battery.fill("");
  await consumption.fill("");
  await expect(soc).toHaveValue("");
  await expect(battery).toHaveValue("");
  await expect(consumption).toHaveValue("");
  await expect(submit).toBeDisabled();

  await soc.fill("30");
  await expect(soc).toHaveValue("30");
  await soc.pressSequentially(".");
  await expect(soc).toHaveValue("30.");
  await soc.pressSequentially("5");
  await expect(soc).toHaveValue("30.5");

  await battery.fill("55");
  await consumption.fill("");
  await consumption.pressSequentially("0,18");
  await expect(consumption).toHaveValue("0,18");

  await expect(submit).toBeEnabled();
  await submit.click();
  await expect(page.getByText(/No feasible station/i)).toBeVisible();
});
