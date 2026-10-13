import { expect, test } from "@playwright/test";

// Open a task, preview it (MathJax + PDF), draft a sheet and see its PDFs.

test("task preview", async ({ page }) => {
  await page.goto("/tasks");
  await page.getByRole("link", { name: "dlp.shanks" }).click();
  await expect(page.getByRole("heading", { name: "dlp.shanks" })).toBeVisible();

  const cards = page.getByTestId("instance");
  await expect(cards).toHaveCount(3);
  await expect(cards.first().locator("mjx-container svg").first()).toBeVisible();
  await page.screenshot({ path: "test-results/task-preview.png" });

  await page.getByText("PDF", { exact: true }).click();
  await page.getByRole("button", { name: "Build PDF" }).click();
  await expect(page.getByTestId("pdf-viewer").locator("canvas").first()).toBeVisible();
  await page.screenshot({ path: "test-results/task-pdf.png" });
});

test("sheet draft", async ({ page }) => {
  await page.goto("/sheets");
  await page.getByRole("link", { name: "Семинар. Дискретное логарифмирование и решётки" }).click();
  await expect(page.getByText("sheets/sem2/seminar-demo.yaml").first()).toBeVisible();
  await page.screenshot({ path: "test-results/sheet-form.png" });

  await page.getByRole("button", { name: "Draft", exact: true }).click();
  const viewers = page.getByTestId("pdf-viewer");
  await expect(viewers).toHaveCount(2);
  await expect(viewers.nth(0).locator("canvas").first()).toBeVisible();
  await expect(viewers.nth(1).locator("canvas").first()).toBeVisible();
  await page.screenshot({ path: "test-results/sheet-draft.png" });
});
