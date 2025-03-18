%% figBase_a.m
%
%   [+] Autor: David Carrascal <david.carrascal@uah.es> 
%
%   [+] Fecha: 10 Mar 2025
clc
close all
clear variables

% VAR
init = 0;
fin = 95;
result_path = '../results/results_v14/ieee123/';

% Preparamos la matriz de datos 
data3d = zeros(4, 13, fin-init+1); % Se reduce a 4 criterios

% Número de criterios y balance de potencias (excluyendo distancia)
num_criteria = 4;
data_power = zeros(num_criteria, fin-init+1, 3);

% Obtenemos los datos de los ficheros csv indicados
for i = init:fin
    file_path = fullfile(result_path, strcat("csv/outdata_d", num2str(i), ".csv"));
    data_table = readtable(file_path, 'NumHeaderLines', 1);
       
    % Pasamos a matriz y filtramos los criterios
    data = data_table{:,:};
    selected_criteria = [1, 3, 4, 5]; % Se eliminó el criterio de distancia
    data3d(:, :, i-init+1) = data(selected_criteria, :);
    data_power(:, i-init+1, :) = data(selected_criteria, [2 4 6]);

end

% Obtenemos las medias y los errores estándar
data_avg = mean(data3d(:, [2 4 6], :), 3);
sem = std(data3d(:, [2 4 6], :), [], 3) / sqrt(fin-init+1);

data_avg_flux = mean(data3d(:, [3 5 7], :), 3);
sem_flux = std(data3d(:, [3 5 7], :), [], 3) / sqrt(fin-init+1);

time_avg = mean(data3d(:, [8 9 10], :), 3);
sem_time = std(data3d(:, [8 9 10], :), [], 3) / sqrt(fin-init+1);

iter_avg = mean(data3d(:, [11 12 13], :), 3);
sem_iter = std(data3d(:, [11 12 13], :), [], 3) / sqrt(fin-init+1);

%% FIGURA 1: Potencias
h1 = figure();
set(gcf, 'Position', [100, 100, 1200, 500]);

% Layout para minimizar espacios
tiledlayout(1,2, 'TileSpacing', 'loose', 'Padding', 'loose');

% Subplot 1 - Balance de Potencias Global
nexttile;
plotBarWithErrors(data_avg, sem, "Average Global Power Balance", "Power (kW)");

% Subplot 2 - Flujo absoluto de potencia
nexttile;
plotBarWithErrors(data_avg_flux, sem_flux, "Average Absolute value of Power-flow", "Power (kW)");

% Crear una leyenda global
hL1 = legend("Ideal", "Lossy", "Lossy & Cap.", 'location','southoutside', 'Orientation','horizontal','FontSize', 10);
hL1.Position(1) = 0.4;
hL1.Position(2) = 0.01;

% Guardar la figura
exportgraphics(h1, fullfile(result_path, 'fig/fig_base_global_powers.pdf'));


%% FIGURA 2: Tiempos e Iteraciones
h2 = figure();
set(gcf, 'Position', [100, 100, 1200, 500]);

% Layout para minimizar espacios
tiledlayout(1,2, 'TileSpacing', 'loose', 'Padding', 'loose');

% Subplot 1 - Tiempos de cálculo
nexttile;
plotBarWithErrors(time_avg, sem_time, "Average Total convergence time", "Time (ms)");

% Subplot 2 - Iteraciones necesarias
nexttile;
plotBarWithErrors(iter_avg, sem_iter, "Average Iterations to convergence", "Number of iterations");

% Crear una leyenda global
hL2 = legend("Ideal", "Lossy", "Lossy & Cap.", 'location','southoutside', 'Orientation','horizontal','FontSize', 10);
hL2.Position(1) = 0.40;
hL2.Position(2) = 0.01;

% Guardar la figura
exportgraphics(h2, fullfile(result_path, 'fig/fig_base_global_time_iter.pdf'));



%% FIGURAS TEMPORAL BALANCE

% Intervalo de tiempo en minutos (cada delta representa 15 minutos)
time_vector = datetime(2025, 2, 14, 0, 0, 0) + minutes(15 * (0:(fin-init)));

% Nombres de los criterios (sin distancia)
criteria_labels = {'Hops', 'Low-Link Losses', 'Power2Zero', 'Power2Zero + Losses'};

% Tipos de markers
criteria_markers = {'-o', '-+', '-^', '-*'};
    
% Títulos de las figuras
case_titles = {"Ideal", "Lossy", "Lossy & Cap."};
    
for j = 2:3
    h = figure();
    set(gcf, 'Position', [100 100 1700 1000]);
    tiledlayout(2,1, 'TileSpacing', 'loose', 'Padding', 'loose');
    nexttile;
    hold on;
    box on;
    % Dibujar el ground truth
    plot(time_vector, data_power(1, :, 1), '-', 'Color','black', 'LineWidth', 3, 'DisplayName', 'Ideal');
        
    % Dibujar las curvas para cada criterio
    for c = 1:num_criteria
        plot(time_vector, data_power(c, :, j), criteria_markers{c}, 'LineWidth', 1.5, 'DisplayName', criteria_labels{c});
    end
        
    grid on;
    grid minor;
    xlabel('Time');
    ylabel('Power (kW)');
    title("Temporal Power Balance - " + case_titles{j});
    %legend('Location', 'best');
    hold off;

    nexttile;
    hold on;
    box on;

    % Dibujar el ground truth
    plot(time_vector, zeros(1,96), '-', 'Color','black', 'LineWidth', 3, 'DisplayName', 'Ideal');

    % Dibujar las curvas para cada criterio con las diferencias con
    % respecto al ideal
    for c = 1:num_criteria
        plot(time_vector, abs(data_power(1, :, 1) - data_power(c, :, j)), criteria_markers{c}, 'LineWidth', 1.5, 'DisplayName', criteria_labels{c});
    end
    grid on;
    grid minor;
    xlabel('Time');
    ylabel('Power (kW)');
    title("Difference respect Ideal");
    %legend('Location', 'best');
    hold off;

    hL2 = legend("Ideal", 'Hops', 'Low-Link Losses', 'Power2Zero', 'Power2Zero + Losses', 'location','southoutside', 'Orientation','horizontal','FontSize', 10);
    hL2.Position(1) = 0.37;
    hL2.Position(2) = 0.01;

    % Exportamos las cosas a lo nico style :)
    exportgraphics(h, fullfile(result_path, strcat('fig/fig_base_TempPowerBalance_', case_titles{j}, '.pdf')));
end


%% FUNCIÓN AUXILIAR: BARRAS CON ERRORES
function plotBarWithErrors(data_avg, sem, title_str, ylabel_str)
    bar_handle = bar(data_avg, 0.6, 'grouped', 'FaceColor', 'flat'); hold on;
    
    % Error bars
    ngroups = size(data_avg, 1);
    nbars = size(data_avg, 2);
    groupwidth = min(0.6, nbars/(nbars + 1.5));
    
    for i = 1:nbars
        x = bar_handle(i).XEndPoints;
        errorbar(x, data_avg(:, i), sem(:, i), 'k', 'linestyle', 'none', 'CapSize', 10);
    end
    
    grid on;
    title(title_str, 'FontSize', 14);
    ylabel(ylabel_str);
    set(gca, 'XTickLabel', {'Hops', 'Low-Link Losses', 'Power2Zero', 'Power2Zero + Losses'}, 'XTickLabelRotation', 0);

    hold off;
end
