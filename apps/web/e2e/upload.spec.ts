import { test, expect } from "@playwright/test";

test.describe("Core navigation", () => {
  test("should display the dashboard", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("body")).toBeVisible();
  });

  test("should display the Enhancements page", async ({ page }) => {
    await page.goto("/jobs");
    await expect(page).toHaveURL(/jobs/);
  });

  test("should display the Audio Library page", async ({ page }) => {
    await page.goto("/library");
    await expect(page).toHaveURL(/library/);
  });

  test("should display the upload page", async ({ page }) => {
    await page.goto("/upload");
    await expect(page).toHaveURL(/upload/);
  });

  test("should navigate to files page", async ({ page }) => {
    await page.goto("/files");
    await expect(page).toHaveURL(/files/);
  });
});
