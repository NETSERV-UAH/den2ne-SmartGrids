% plot_complexity_no_errorbar_long.m
% Igual que antes, pero la figura tendrá un formato más largo (ancho aumentado)

% Directorio de resultados
resultsDir = 'results_spread_ids';
csvFiles   = dir(fullfile(resultsDir, 'topo_*.csv'));

% Prealocar vectores
numTopos   = length(csvFiles);
topoSizes  = zeros(numTopos,1);
avgSpread  = zeros(numTopos,1);
avgMST     = zeros(numTopos,1);
avgPSO     = zeros(numTopos,1);
avgGA      = zeros(numTopos,1);

% Procesar cada CSV
for k = 1:numTopos
    fname = csvFiles(k).name;
    tok = regexp(fname, 'topo_(\d+)\.csv', 'tokens');
    topoSizes(k) = str2double(tok{1}{1});
    T = readtable(fullfile(resultsDir, fname));
    avgSpread(k) = mean(T{:, 'SpreadIDs_s_'});
    avgMST(k)    = mean(T{:, 'MST_s_'});
    avgPSO(k)    = mean(T{:, 'PSO_s_'});
    avgGA(k)     = mean(T{:, 'GA_s_'});
end

% Ordenar por tamaño
[topoSizes, idx] = sort(topoSizes);
avgSpread = avgSpread(idx);
avgMST    = avgMST(idx);
avgPSO    = avgPSO(idx);
avgGA     = avgGA(idx);

% Crear figura más larga
figure('Units','normalized','Position',[0.05 0.1 0.9 0.5]);  % [left bottom width height]

hold on;
plot(topoSizes, avgSpread, 'o-','LineWidth',1.5);
plot(topoSizes, avgMST,    's-','LineWidth',1.5);
plot(topoSizes, avgPSO,    'd-','LineWidth',1.5);
plot(topoSizes, avgGA,     '^-','LineWidth',1.5);

xlabel('Graph size (nodes)', 'Fontsize', 14);
ylabel('Tiempo medio de ejecución [s]', 'Fontsize', 14);
title('Complejidad computacional comparativa', 'Fontsize', 16);
legend({'Spread IDs','MST','PSO','GA'}, 'Location','northwest','Fontsize', 14);
grid on;
set(gca, 'YScale', 'log');  % Escala logarítmica en el eje Y

ax=gca;
ax.XAxis.FontSize = 12;
ax.YAxis.FontSize = 12;

% Exportar la figura a PDF vectorial
outputFile = fullfile(resultsDir, 'complexity_comparison_time.pdf');
exportgraphics(gcf, outputFile, 'ContentType','vector');

hold off;
